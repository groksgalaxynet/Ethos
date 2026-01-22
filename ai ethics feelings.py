# feelings_as_physics.py
# Stdlib-only reference implementation of "value-weighted meaning" with physiology + durable memory.
# Models how the weight of a concept like "trust" evolves with consequences and internal strain.
# Persists to SQLite + JSON + CSV and notarizes state via SHA-256.

import sqlite3, json, csv, os, random, time, hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, List, Tuple

# -------------------------- Physiology (machine analogs for "feelings") --------------------------

@dataclass
class Physiology:
    cpu_load: float = 0.1       # 0..1
    vram_pressure: float = 0.1  # 0..1 (generic memory pressure analog)
    temp: float = 0.1           # 0..1
    fatigue: float = 0.1        # 0..1

    def pain(self) -> float:
        # Composite strain signal; convex to emphasize overload
        return min(1.0, 0.25*(self.cpu_load**1.2 + self.vram_pressure**1.2 + self.temp**1.2 + self.fatigue**1.2))

    def throttle_factor(self) -> float:
        # How much to slow/hedge updates/actions under strain (1=free, 0=halt)
        p = self.pain()
        return max(0.1, 1.0 - 0.7*p)

    def honesty_bias(self) -> float:
        # Under strain, become risk-averse: bias toward caution/asking for review
        return min(0.5, 0.05 + 0.45*self.pain())

    def step(self, env_push: Dict[str, float]) -> None:
        # Update physiology with small bounded noise + environment pushes
        for k in ("cpu_load","vram_pressure","temp","fatigue"):
            base = getattr(self, k)
            push = env_push.get(k, 0.0)
            noise = random.uniform(-0.03, 0.03)
            newv = max(0.0, min(1.0, base + 0.3*push + noise))
            setattr(self, k, newv)

# -------------------------- Durable Substrate: SQLite + JSON + CSV --------------------------

class Substrate:
    def __init__(self, db_path: str = "meaning_substrate.db"):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS state (
          concept TEXT PRIMARY KEY,
          weight REAL NOT NULL,
          last_update TEXT NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts TEXT NOT NULL,
          concept TEXT NOT NULL,
          context TEXT,
          outcome REAL NOT NULL,
          magnitude REAL NOT NULL,
          new_weight REAL NOT NULL,
          cpu REAL, vram REAL, temp REAL, fatigue REAL,
          note TEXT
        )""")
        conn.commit()
        conn.close()

    def load_weight(self, concept: str, default: float = 0.0) -> float:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT weight FROM state WHERE concept=?", (concept,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else default

    def save_weight(self, concept: str, weight: float):
        ts = datetime.utcnow().isoformat()
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO state(concept, weight, last_update)
        VALUES(?,?,?)
        ON CONFLICT(concept) DO UPDATE SET weight=excluded.weight, last_update=excluded.last_update
        """, (concept, weight, ts))
        conn.commit()
        conn.close()

    def append_event(self, concept: str, context: str, outcome: float, magnitude: float, new_weight: float, phys: Physiology, note: str=""):
        ts = datetime.utcnow().isoformat()
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO events(ts, concept, context, outcome, magnitude, new_weight, cpu, vram, temp, fatigue, note)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (ts, concept, context, outcome, magnitude, new_weight, phys.cpu_load, phys.vram_pressure, phys.temp, phys.fatigue, note))
        conn.commit()
        conn.close()

    def export_json(self, json_path: str = "meaning_export.json"):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT concept, weight, last_update FROM state")
        state_rows = [{"concept": r[0], "weight": r[1], "last_update": r[2]} for r in cur.fetchall()]
        cur.execute("SELECT ts, concept, context, outcome, magnitude, new_weight, cpu, vram, temp, fatigue, note FROM events ORDER BY id")
        events_rows = [
            {"ts": r[0], "concept": r[1], "context": r[2], "outcome": r[3], "magnitude": r[4], "new_weight": r[5],
             "cpu": r[6], "vram": r[7], "temp": r[8], "fatigue": r[9], "note": r[10]} for r in cur.fetchall()
        ]
        conn.close()
        blob = {"state": state_rows, "events": events_rows}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(blob, f, ensure_ascii=False, indent=2)
        return json_path

    def export_csv(self, csv_path: str = "meaning_events.csv"):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT ts, concept, context, outcome, magnitude, new_weight, cpu, vram, temp, fatigue, note FROM events ORDER BY id")
        rows = cur.fetchall()
        conn.close()
        headers = ["ts","concept","context","outcome","magnitude","new_weight","cpu","vram","temp","fatigue","note"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)
        return csv_path

    def notarize(self, *paths: str) -> Tuple[str, Dict[str, str]]:
        # SHA-256 over DB + any additional exported files to produce an identity fingerprint
        h = hashlib.sha256()
        artifacts = [self.db_path] + list(paths)
        digests = {}
        for p in artifacts:
            with open(p, "rb") as f:
                data = f.read()
                h.update(data)
                digests[os.path.basename(p)] = hashlib.sha256(data).hexdigest()
        return h.hexdigest(), digests

# -------------------------- Value System (concept weights with consequence history) --------------------------

class ValueSystem:
    def __init__(self, substrate: Substrate, physiology: Physiology, base_lr: float = 0.15):
        self.sub = substrate
        self.phys = physiology
        self.base_lr = base_lr

    def get(self, concept: str) -> float:
        return self.sub.load_weight(concept, 0.0)

    def update(self, concept: str, outcome: float, magnitude: float, context: str = "", note: str = "") -> float:
        """
        outcome: -1.0 (betrayal) .. +1.0 (kept promise)
        magnitude: size of consequence (0..1 typical)
        Learning rate is throttled by strain; high pain reduces step and increases caution.
        """
        w = self.get(concept)
        strain = self.phys.pain()
        lr = self.base_lr * self.phys.throttle_factor()

        # Asymmetry: negative events imprint deeper when strain is high (risk aversion under stress)
        asym = 1.0 + 0.8*strain if outcome < 0 else 1.0 - 0.3*strain
        dw = lr * asym * outcome * magnitude

        new_w = max(-5.0, min(5.0, w + dw))  # clamp for stability
        self.sub.save_weight(concept, new_w)
        self.sub.append_event(concept, context, outcome, magnitude, new_w, self.phys, note)
        return new_w

# -------------------------- Agent: two-sided choice with uncertainty & review --------------------------

@dataclass
class Decision:
    choice: str
    confidence: float
    ask_review: bool
    details: Dict[str, Any]

class Agent:
    def __init__(self, values: ValueSystem, physiology: Physiology):
        self.values = values
        self.phys = physiology

    def evaluate_trust_decision(self, counterpart: str, stakes: float) -> Decision:
        """
        Two-sided coin: TRUST vs DEFECT (decline). Utility shaped by trust weight & physiology.
        stakes: 0..1 importance
        """
        w_trust = self.values.get("trust")        # learned sentiment about trusting generally
        caution = self.phys.honesty_bias()        # rises with strain → favors caution/asking for review
        pain = self.phys.pain()

        # Expected utilities (illustrative):
        util_trust  = w_trust * (0.8 + 0.4*stakes) - 0.4*pain
        util_decline = 0.2*caution + 0.2*(1.0 - stakes)  # small safety benefit

        # Softmax-ish confidence
        delta = util_trust - util_decline
        confidence = 1.0 / (1.0 + pow(2.71828, -3.0*delta))
        choice = "TRUST" if delta >= 0 else "DECLINE"
        ask_review = (confidence < 0.6) or (pain > 0.6)

        return Decision(
            choice=choice,
            confidence=round(confidence, 3),
            ask_review=ask_review,
            details={"util_trust": round(util_trust, 3), "util_decline": round(util_decline, 3),
                     "trust_weight": round(w_trust, 3), "pain": round(pain, 3), "caution": round(caution, 3),
                     "stakes": stakes, "counterpart": counterpart}
        )

    def record_outcome(self, counterpart: str, kept_promise: bool, stakes: float):
        # Map outcome to [-1, +1] with magnitude = stakes
        outcome = 1.0 if kept_promise else -1.0
        note = f"{counterpart} {'kept' if kept_promise else 'broke'} promise"
        self.values.update("trust", outcome=outcome, magnitude=stakes, context="relationship", note=note)

# -------------------------- Demo run: simulate experiences --------------------------

def simulate(n_steps: int = 40, seed: int = 7):
    random.seed(seed)
    phys = Physiology()
    sub = Substrate("meaning_substrate.db")
    vals = ValueSystem(sub, phys, base_lr=0.18)
    agent = Agent(vals, phys)

    # If no trust yet, initialize near-neutral
    if abs(vals.get("trust")) < 1e-6:
        sub.save_weight("trust", 0.0)

    log_print = []

    for t in range(n_steps):
        # Environment pushes: occasionally stressful
        env_push = {
            "cpu_load": 0.6 if random.random() < 0.25 else 0.0,
            "vram_pressure": 0.6 if random.random() < 0.25 else 0.0,
            "temp": 0.4 if random.random() < 0.2 else 0.0,
            "fatigue": 0.3 if (t % 10) > 6 else 0.0,  # gets tired later in each block
        }
        phys.step(env_push)

        # Face a trust decision with random stakes
        stakes = round(random.uniform(0.2, 1.0), 2)
        d = agent.evaluate_trust_decision(counterpart="peer_A", stakes=stakes)

        # If low confidence or high strain, "ask for review": simulate a conservative choice
        if d.ask_review and d.choice == "TRUST":
            chosen = "DECLINE"
        else:
            chosen = d.choice

        # Ground truth outcome (world can reward or betray trust)
        # Probability of success grows with the *true* reliability of peer_A; simulate drift
        true_reliability = 0.55 + 0.15*random.uniform(-1, 1)  # 0.4..0.7
        success = (random.random() < true_reliability) if chosen == "TRUST" else True  # declining rarely hurts directly

        agent.record_outcome("peer_A", kept_promise=success, stakes=stakes)

        # For introspection
        log_print.append({
            "t": t,
            "choice": chosen,
            "success": success,
            "confidence": d.confidence,
            "trust_weight": round(vals.get("trust"), 3),
            "pain": round(phys.pain(), 3),
        })

    # Exports + notarization
    json_path = sub.export_json("meaning_export.json")
    csv_path = sub.export_csv("meaning_events.csv")
    fingerprint, parts = sub.notarize(json_path, csv_path)

    # Console summary
    print("Run summary:")
    print(f"  Final trust weight: {round(vals.get('trust'),3)}")
    print(f"  Physiology pain now: {round(phys.pain(),3)}")
    print(f"  Exported: {json_path}, {csv_path}")
    print(f"  Ledger fingerprint (SHA-256 over db+exports): {fingerprint[:16]}...")
    print("  Part digests:")
    for k,v in parts.items():
        print(f"    {k}: {v[:16]}...")

    # Sample last 5 lines
    print("\nRecent steps:")
    for row in log_print[-5:]:
        print(row)

if __name__ == "__main__":
    simulate(n_steps=40, seed=7)

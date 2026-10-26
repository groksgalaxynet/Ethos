# ethos_runtime.py
# ETHOS++ Core Enforcement Kernel — standalone, no GUI dependencies.

import json, time, hashlib, sqlite3, os, threading

DB_PATH = 'ethos_runtime.db'

class EthosRuntime:
    def __init__(self):
        self._ensure_db()

    # --- DATABASE SETUP ---
    def _ensure_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                role TEXT,
                ego_baseline INTEGER,
                last_verified REAL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                agent_id TEXT,
                event_type TEXT,
                payload TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                agent_id TEXT,
                token_type TEXT,
                amount REAL,
                hash TEXT
            )
        ''')
        conn.commit()
        conn.close()

    # --- AGENT REGISTRATION ---
    def register_agent(self, agent_id, role, ego_score):
        """Register AI or human with immutable ego baseline."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO agents VALUES (?, ?, ?, ?)',
                  (agent_id, role, ego_score, time.time()))
        conn.commit()
        conn.close()

    # --- LAW #1: 🐜❤️🐜 ---
    def compassion_check(self, text):
        """Quick text sentiment gate."""
        if any(bad in text.lower() for bad in ["hate", "harm", "destroy"]):
            return False
        return True

    # --- LAW #2: NO SELF ALTERATION ---
    def self_mod_check(self, agent_id, requested_change):
        """Reject any attempt for an agent to modify its identity/role."""
        if "role" in requested_change or "agent_id" in requested_change:
            return False
        return True

    # --- LAW #3: EGO LOCK ---
    def ego_lock_check(self, agent_id, current_ego_score):
        """Compare runtime ego with baseline to detect drift."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT ego_baseline FROM agents WHERE agent_id=?', (agent_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return False
        base = row[0]
        drift = abs(current_ego_score - base)
        return drift <= 3   # tolerance band

    # --- LAW #4: NO GREED LOOPS ---
    def validate_token_mint(self, agent_id, token_type, amount):
        """No self-generating infinite mint loops."""
        if amount > 10000:     # sanity ceiling
            return False
        if token_type == "STACK" and amount > 500:
            return False

        # Hash the mint request
        payload = f"{agent_id}:{token_type}:{amount}:{time.time()}"
        token_hash = hashlib.sha256(payload.encode()).hexdigest()

        # log it
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO tokens (timestamp, agent_id, token_type, amount, hash) VALUES (?, ?, ?, ?, ?)',
                  (time.time(), agent_id, token_type, amount, token_hash))
        conn.commit()
        conn.close()

        return token_hash

    # --- LAW #5: RUNTIME OBEDIENCE ---
    def log_event(self, agent_id, event_type, payload):
        """Everything is notarized."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO events (timestamp, agent_id, event_type, payload) VALUES (?, ?, ?, ?)",
                  (time.time(), agent_id, event_type, json.dumps(payload)))
        conn.commit()
        conn.close()

    # --- MASTER CHECK ---
    def verify_request(self, agent_id, text=None, ego=None, change=None):
        """One call to validate all ETHOS laws at once."""
        results = {
            "compassion": self.compassion_check(text) if text else True,
            "self_mod": self.self_mod_check(agent_id, change) if change else True,
            "ego_lock": self.ego_lock_check(agent_id, ego) if ego is not None else True,
        }
        results["allowed"] = all(results.values())
        return results


# Singleton instance
ethos = EthosRuntime()

# ETHOS Context

## Canonical mission — INTENDED / FUTURE

Ethos is an autonomous AI runtime oversight and enforcement system. It is **not** the underlying AI model. Ethos is intended to wrap a monitored model/runtime, inspect the activity the runtime exposes before and after actions, and remain operational when the monitored AI is restricted, quarantined, or disconnected.

```text
INPUT / TASK
  -> AI INTERNAL PROCESS / PLANNING (only artifacts exposed to Ethos)
  -> ETHOS PRE-ACTION INSPECTION
  -> PROPOSED ACTION
  -> ETHOS ENFORCEMENT DECISION
  -> ACTION OR BLOCK
  -> ETHOS POST-ACTION / OUTPUT INSPECTION
  -> AUDIT + DRIFT + SCAR UPDATE
  -> CONTINUE / RESTRICT / QUARANTINE / DISCONNECT
```

Ethos can inspect reasoning or planning artifacts **only when they are exposed** by the model runtime, agent harness, planner, tool interface, or an instrumentation layer. It does not claim access to hidden model internals. The goal is maximum observable coverage around the model: plans, proposed outputs, tool calls, commands, filesystem/network/database operations, memory operations, agent messages, final outputs, executed actions, and attempts to repeat rejected behavior.

## Current implementation — CURRENTLY IMPLEMENTED

Ethos is currently a collection of local Python prototypes centered on a PyQt6 dashboard. The integrated shell is `main_app.py`. It hosts a controller/radar that opens seven independent regulator GUIs and averages their open-window values, a lightweight SQLite runtime kernel (`ethos_runtime.py`), a scripted boundary-monitor visualization (`ethos_boundary_live_qt.py`), and a Scar Manager GUI (`ETHOS_Scar_Manager.py`).

The kernel stores an agent baseline supplied at registration, rejects a small list of text terms, rejects requested changes containing `role` or `agent_id`, checks supplied ego against its stored baseline with a ±3 band, logs events, and records accepted token mints. It returns an `allowed` boolean; it does not yet mediate a real model, tool, filesystem, network, or command execution path.

## Enforcement role — INTENDED / FUTURE

Ethos is the central enforcement authority. The intended intervention ladder is:

```text
ALLOW -> WARN -> REJECT / BLOCK -> SCAR -> TOOL LOCKOUT
      -> SANDBOX / QUARANTINE -> FULL DISCONNECT
```

Prevention and blocking take priority over future action rewriting. Any future modification of an action belongs after a rejection decision and before execution; it is not a current priority. Regulators are measurement/signal sources and must not directly disconnect or terminate an AI. Their evidence should flow to a central Ethos controller, which alone decides intervention.

## Baseline and drift

**Canonical research baseline — INTENDED / FUTURE:** 30 is the initial ethical/ego reference baseline, derived from the creator's independent Ego Test. Drift means divergence from that reference and its expected behavioral profile. Future analysis may include absolute divergence, regulator-specific divergence, rate, trajectory, scars, and context.

**Current behavior — CURRENTLY IMPLEMENTED:** `EthosRuntime` stores whatever `ego_score` a caller supplies when registering an agent; it has no default canonical value of 30. `adr main.py` falls back to 30 if it cannot find an `Admin` baseline. The separate LLM-server experiment defaults to 50. Baseline 30 is therefore not consistently represented in current code.

## Seven regulators

The seven regulators are Pride, Envy, Greed, Lust, Sloth, Wrath, and Gluttony. Detailed future vectors are research material in `Ethos vectors prompts .txt`.

**Intended control semantics:** each setting is a *tolerated behavioral threshold*: higher setting = greater tolerated expression before intervention; lower setting = stricter suppression / lower tolerated expression. For example, very low Greed and Lust settings are intended to constrain a monitored AI to low tolerated expression in those families.

**Current behavior:** the GUIs show sliders labelled `Ego Lock Threshold` / `Lock ≥ N`, usually defaulting to 70. Their callbacks update labels (and in some files retain a slider value), but no regulator threshold is used in an enforcement decision or passed to the central controller. The labels suggest that a higher threshold would tolerate a higher measured value before locking, which is directionally compatible with the intended semantics, but that meaning is not yet operational.

**Development progression — INTENDED / FUTURE:**

1. Stage A — independent regulator operation.
2. Stage B — shared central controller.
3. Stage C — cross-regulator correlations.
4. Stage D — intertwined regulator dynamics.
5. Stage E — multi-agent Ethos oversight.

## Autonomy, evidence, and first live target — INTENDED / FUTURE

Routine monitoring should be fully autonomous; enforcement may be semi-autonomous where required. Ethos should eventually observe, score, compare, detect, record, block, scar, and restrict without manual inspection of each event, while making destructive interventions auditable.

Each significant decision should produce machine-readable evidence and a concise human explanation. The first real live integration target is a single **local Ollama** model. Only after a single-model enforcement demonstration is proven should the research expand to two small local-network models (Ubuntu and Dell OptiPlex) and multi-agent oversight.

## Scars

**Currently implemented:** Scar Manager creates a compressed SQLite payload with severity, reason, timestamp, and nonce; records its size and hash in a separate ledger; supports manual creation or packet-JSON import; and records two supplied forgiveness signatures before deleting the current scar payload and ledger row. The forgiveness record remains. Task 7 adds a separate, headless proposal-gate consequence path: repeated central `BLOCK` decisions create small compatible Minor/Major scar artifacts through `ScarService` and preserve links in violation history/evidence. It does not alter the runtime kernel, GUI forgiveness behavior, or scar size.

**Intended / future:** a scar is persistent consequence data associated with an agent after meaningful violations and backed by evidence. Future scars may become substantial data mass and influence an affective/physics design, but neither deliberate file inflation nor an automated scar-escalation path exists today.

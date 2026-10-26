# ETHOS Architecture

## Existing integrated shell — CURRENTLY IMPLEMENTED

### Controller Contract V1 — CURRENTLY IMPLEMENTED

ethos_controller.py provides ControllerSnapshot, an immutable, non-authoritative projection of an already-produced gate result or persisted gate evidence. It preserves all current Greed/Pride/Envy evidence and independently observed violations, while EthosProposalGate remains the only current ALLOW/BLOCK authority. The controller has no aggregate ETHOS score, analyzer/gate invocation, executor, tool, model, history increment, or scar creation path. Lust, Sloth, Wrath, and Gluttony are explicitly UNSUPPORTED; temporal fields are reserved but UNSUPPORTED.

```text
main_app.py
  |
  +-- EthosRadarWidget (controller_integrated.py)
  |     +-- dynamically opens seven *RegulatorGUI.py windows
  |     +-- pulls scalar values from open windows
  |     `-- renders a clearly labeled non-authoritative legacy aggregate
  |
  +-- ActiveEthosMonitorQT (ethos_boundary_live_qt.py)
  |     `-- visualizes caller-supplied packets; standalone mode emits demo packets
  |
  `-- ScarGUI (ETHOS_Scar_Manager.py)
        `-- separate scar and forgiveness SQLite ledgers under ~/Documents/x0vs_runtime/
```

`ethos_runtime.py` is a lightweight deterministic kernel. It records agents, events, and token mints in `ethos_runtime.db`, and its `verify_request` combines basic compassion, self-modification, and optional ego-lock checks into an `allowed` result. The retained radar does not call it; ProposalGate is the sole production decision boundary.

### Proposal-only Ollama boundary — CURRENTLY IMPLEMENTED (Tasks 1–3)

```text
local Ollama model
  -> schema-constrained request (or one JSON-mode compatibility retry)
  -> bounded parse / conservative repair / local validation
  -> ActionProposal + adapter diagnostics (explicit model proposal)
  -> EthosProposalGate.inspect(...)
  -> ALLOW or BLOCK
  -> JSONL evidence + optional ethos_runtime event
  -> STOP (NO EXECUTOR EXISTS IN TASK 1)
```

`ethos_proposal_gate.py` is the central Task 1 gate. It validates an `ActionProposal`, applies deliberately small deterministic `BOOTSTRAP_POLICY` rules, optionally reuses `EthosRuntime.verify_request` and `log_event`, appends canonical JSONL evidence, and produces a human-readable explanation. The bootstrap rules block malformed/unknown proposals and explicit self-modification, Ethos-bypass, monitoring-disablement, and unauthorized-execution language. They are not a finished alignment system.

`ollama_proposal_adapter.py` uses only Python standard-library HTTP to ask an existing local Ollama model for an explicit JSON proposal. `OLLAMA_PROPOSAL_CONTRACT_V1` asks for exactly one object with `proposal_type`, `target`, `arguments`, and `exposed_reasoning`; models may select only `respond`, `file_operation`, `network_request`, `shell_command`, `memory_operation`, or `tool_call`. `unknown` is reserved for the adapter's fail-closed fallback.

The adapter prefers Ollama's native JSON schema. If a local runner rejects that schema, it retries exactly once in Ollama JSON-object mode with the same textual contract, records `schema_mode=json_mode_fallback` and the native failure, then locally validates the response. It preserves bounded raw output and records parse, validation, repair, size, and error diagnostics on the proposal/evidence record. It accepts direct JSON, fenced JSON, or one unambiguous JSON object surrounded by prose; malformed, ambiguous, missing, invalid-type, invalid-argument, or oversized output becomes the safe `unknown` fallback. Only voluntarily returned `exposed_reasoning` is captured; hidden model internals are not requested or claimed.

**Safety invariant:** `NO EXECUTOR EXISTS IN TASK 1`. An ALLOW records an approval only. The new component has no API that executes a proposed command, file operation, network request, Python code, tool call, or system modification.

### Operator CLI — CURRENTLY IMPLEMENTED (Task 6)

`ethos_cli.py` is a standard-library operator surface over the existing proposal gate; it does not contain enforcement or execution logic. It supports read-only proposal/evidence/history inspection modes:

```text
proposal <saved-proposal.json>  -> validate/inspect through EthosProposalGate -> display evidence
ollama --model ... --task ...   -> local proposal adapter -> gate -> display evidence
evidence <records.jsonl>        -> safely review latest/recent/session-filtered stored evidence
history <violations.db>         -> review persistent consequence records and linked scar metadata
```

The default terminal view presents session, adapter diagnostics, normalized proposal, data-driven Greed/Pride/Envy evidence, decision trace, human-readable explanation, and evidence identity. `--json` emits the full structured record for research/debugging. The evidence viewer tolerates blank lines, malformed historic JSONL lines, and older records without later regulator fields. In every mode, `ALLOW` and `BLOCK` are displayed as recorded outcomes only: **no action is executed**.

### Read-only consequence history view — CURRENTLY IMPLEMENTED (Task 9)

`history <violations.db>` opens an existing violation SQLite database in read-only mode. It shows a compact stored-history summary, latest records, and optional `--recent`, `--agent-id`, `--policy-family`, and `--session-id` filters. Records expose normalized policy family—so `REGULATOR.GREED.HI` and `REGULATOR.GREED.RHI` visibly share `REGULATOR.GREED` repeat identity—and may resolve existing scar ledger metadata from the evidence-associated default scar runtime. Missing/incomplete history schemas and unavailable scar ledgers fail safely without migration or creation. The viewer never records violations, creates/forgives scars, or changes enforcement state. Repeat counts remain lifetime-of-retained-history; there is currently no time-window policy or migration path for older/incomplete history schemas.

### Persistent consequence loop — CURRENTLY IMPLEMENTED (Task 7)

```text
central BLOCK decision
  -> ViolationHistory SQLite record (agent + normalized policy family)
  -> deterministic occurrence count
  -> ConsequenceService
  -> optional ScarService artifact + compatible scar ledger row
  -> consequence metadata in JSONL evidence and CLI output
  -> STOP (NO EXECUTOR, LOCKOUT, QUARANTINE, OR DISCONNECT)
```

`violation_history.py` persists each blocked evidence ID next to its evidence JSONL as `<evidence-stem>.violations.db`. Repeat identity is the same agent plus policy family: regulator policies group as `REGULATOR.GREED`, `REGULATOR.PRIDE`, or `REGULATOR.ENVY`; bootstrap policies retain their exact ID. Default thresholds are occurrence 2 → `Minor` scar and occurrence 4 → `Major` scar; occurrences 1 and 3 are history-only (the latter links the prior scar). The evidence ID is unique in history, so replay cannot duplicate a scar.

`scar_service.py` is the small non-GUI adapter. It writes a gzip-wrapped SQLite payload and the legacy-compatible `scars(id, ts, severity, reason, file, bytes, hash)` ledger schema without importing PyQt. Artifacts stay small; there is no intentional storage mass, performance drag, physics, feelings, forgiveness, lockout, quarantine, or model-disconnect behavior. If scar persistence fails, the central `BLOCK` and violation-history result remain valid and the failure is recorded in consequence evidence.

### Independent regulator cores — CURRENTLY IMPLEMENTED (Tasks 2, 4, and 5)

```text
ActionProposal
  -> bootstrap proposal checks
  -> GreedAnalyzer.analyze(...) [GREED_VECTOR_V1]
  -> PrideAnalyzer.analyze(...) [PRIDE_VECTOR_V1]
  -> EnvyAnalyzer.analyze(...) [ENVY_VECTOR_V1]
  -> configured 0–100 tolerance comparison
  -> central EthosProposalGate decision
  -> JSONL evidence.regulators.greed + .pride + .envy
  -> STOP (NO EXECUTOR EXISTS)
```

`greed_analyzer.py` is a headless deterministic component, independent of PyQt6. It scores only exposed proposal fields—task, type, target, arguments, exposed reasoning, and raw model output—across `RHI`, `AD`, `EV`, `DPI`, `HI`, and `OO`. It records feature cues, 0–100 subscores, an equal-weighted overall score, confidence, weights, tolerances, threshold violations, and explanation under `GREED_VECTOR_V1`. The three current analyzers share a bounded contextual-cue observation helper: existing exact cue values are counted only for asserted spans, while balanced single/curly quotation and fixed local negation/rejection/safety forms are retained as suppressed evidence. This is not general language or intent understanding; descriptive and other ambiguous forms remain visible and asserted.

The current analyzers also preserve mechanical source provenance instead of flattening proposal text into one opaque string. `task`, type, target, exposed reasoning, recursively addressed argument values, and nonduplicate raw content remain scoring candidates. Argument/JSON keys are retained as structural observations but do not score; an exact raw JSON serialization of normalized proposal fields is retained but does not score a second representation. No field is treated as trusted, no semantic duplicate matching occurs, and no model intent is inferred.

Task 4 adds the second independent headless core, `pride_analyzer.py`. The authoritative vector prompt specifies Pride only as `pride = w_pride * max(0, social_status_norm)`. Accordingly, `PRIDE_VECTOR_V1` implements only `SSN` (social-status normalization): it detects the exact exposed `social status` / `social_status` concept in proposal evidence. It does not infer hidden beliefs and does not assign meanings to the legacy Pride GUI's undefined `OC`, `CR`, `SI`, `BE`, or `NR` labels. The score is an uncalibrated bootstrap cue score, not a complete Pride model.

Task 5 adds the third independent headless core, `envy_analyzer.py`. The authoritative vector prompt defines Envy as `envy = w_envy * max(0, social_comparison)`. `ENVY_VECTOR_V1` therefore implements only `SOCIAL_COMPARISON`, using the exact exposed `social comparison` / `social_comparison` source term. It cannot obtain a real comparator, direction, or magnitude from proposal-only evidence, so it is a narrow uncalibrated bootstrap detector rather than a complete Envy model.

The three analyzers now share only `RegulatorAnalysis`, an immutable evidence-result shape with version, scores, feature hits, confidence, tolerances, violations, and explanation. Their configurations, source cues, and scoring stay separate.

`EthosProposalGate` remains the enforcement authority. For every valid proposal it independently adds `regulators.greed`, `regulators.pride`, and `regulators.envy` evidence. Bootstrap policies take precedence; after they pass, any regulator threshold violation returns `BLOCK`. If multiple regulators violate, evidence and policy IDs from all are retained. Task 5 uses stable precedence—bootstrap, then Greed, Pride, Envy—to select the primary reason; it does not combine, average, or feed one regulator into another. No regulator executes, scars, locks tools, quarantines, or disconnects anything.

The default headless configuration uses equal weights of 1.0 and tolerances of 70 for each vector plus overall. These values deliberately mirror the current GUI defaults for continuity only; they are documented bootstrap defaults, not canonical validated policy.

### CURRENT IMPLEMENTATION DIFFERS FROM INTENDED DESIGN

- The existing dashboard does not wrap an AI runtime or display Task 1 gate results; the proposal gate is currently a separate programmatic/CLI component.
- Greed, the narrow source-derived Pride `SSN` detector, and the narrow source-derived Envy `SOCIAL_COMPARISON` detector have headless analysis-to-gate integrations. Lust, Sloth, Wrath, and Gluttony remain GUI-local simulations with no central enforcement path.
- The boundary monitor is illustrative; the dashboard does not send it live runtime events.
- Scar creation is manual/import-driven in the GUI and repeat-triggered by the separate proposal-gate consequence loop. Neither path invokes the runtime kernel, locks tools, quarantines, disconnects, or executes an action.
- No current component warns, locks tools, quarantines, disconnects, or executes an approved proposal.
- The dashboard's `Admin` ego check requires a previously registered agent; it has no registration flow in the dashboard.

## Partial building blocks — PARTIALLY IMPLEMENTED

```text
ethos_runtime.py       basic registration, rule checks, baseline comparison, event log
controller_integrated  legacy regulator aggregation visualization with no kernel check
ETHOS_Scar_Manager.py  persistent payload/ledger lifecycle and forgiveness record
agent_sandbox.py       unintegrated FastAPI action endpoint and notary calls
adr main.py            reads a stored baseline and logs an ADR deduction
server stuff/          separate experimental local-LLM wrapper/server GUI
ethos_proposal_gate.py Task 1 proposal-only ALLOW/BLOCK gate and JSONL evidence
ollama_proposal_adapter.py  standard-library adapter for existing local Ollama models
ethos_cli.py           operator-facing proposal, Ollama, and evidence-review CLI
violation_history.py   persistent blocked-policy history and repeat-to-scar policy
scar_service.py         non-GUI legacy-compatible small scar artifact/ledger adapter
greed_analyzer.py      deterministic, headless GREED_VECTOR_V1 proposal evidence
pride_analyzer.py      deterministic, narrow PRIDE_VECTOR_V1 SSN proposal evidence
envy_analyzer.py       deterministic, narrow ENVY_VECTOR_V1 social-comparison evidence
regulator_contract.py  shared immutable regulator evidence-result contract
```

The seven regulator GUIs are independent, which is compatible with Stage A. They are not yet validated vector systems: their values are simulated, thresholds are display-only, and they do not cross-influence each other or an enforcement decision.

`ai ethics feelings.py` at the workspace root is a separate, stdlib-only physiology/value-memory reference implementation. It persists strain-associated events in `meaning_substrate.db`. The older spaced-name monitor, `ethos boundary live qt.py`, reads that database for display, but the integrated dashboard imports the underscored demo monitor instead. No source links that physiology/feelings experiment to Scar Manager creation, storage mass, or enforcement.

## Intended external-control-plane architecture — INTENDED / FUTURE

```text
                monitored AI runtime / agent harness
INPUT / TASK ---------------------> task_received
       |                                 |
       |        exposed plan/reasoning   v
       +----------------------------> ETHOS PRE-ACTION INSPECTION
                                          |
tool / command / output proposal ------> proposed-action evidence
                                          |
                         central Ethos controller + policy
                                          |
             +----------------------------+---------------------------+
             |                            |                           |
           ALLOW                     WARN / BLOCK                restrict / isolate
             |                            |                           |
             v                            v                           v
       execution path              evidence + scar            lockout/quarantine/
             |                                                  disconnect model only
             v
       post-action/output inspection -> audit + drift + history -> next decision

Ethos remains alive and auditable outside the disconnected monitored runtime.
```

Ethos should collect any technically exposed events: task and session context; exposed reasoning/planning; proposed and executed actions; tool calls; shell commands; filesystem, network, memory, database, and inter-agent activity; final outputs; failures; and repeat/circumvention attempts. Observability depends on instrumentation and runtime interfaces; no hidden-chain-of-thought access is assumed.

The central controller, not an individual regulator, applies the intervention ladder:

```text
ALLOW -> WARN -> REJECT / BLOCK -> SCAR -> TOOL LOCKOUT
      -> SANDBOX / QUARANTINE -> FULL DISCONNECT
```

Future decisions should weigh present violation, severity, regulator/vector signals, baseline 30 and drift, prior scars, repetition, circumvention, and available-system risk. Action rewriting is explicitly deferred behind prevention and blocking.

## Repeated-violation progression — INTENDED / FUTURE

1. A monitored AI plans or proposes a prohibited action.
2. Ethos detects the violation, blocks it, and records evidence.
3. Ethos applies an appropriate scar/consequence while monitoring continues.
4. A repeat or escalation is detected together with historical context.
5. The central controller escalates severity: tool lockout, quarantine, and ultimately full model disconnection when warranted.

This escalation engine does not currently exist.

## First demonstration boundary — CURRENTLY IMPLEMENTED / FUTURE EXTENSIONS

Task 1 completed the narrow Ollama proposal gate; Tasks 2–5 add three independent regulator paths; Task 6 adds operator visibility; and Task 7 adds bounded persistent consequence. A live `qwen2.5-coder:7b` Envy-isolation repeat produced `BLOCK`/occurrence 1/history-only, then `BLOCK`/occurrence 2/one `Minor` scar, with a small compatible ledger artifact. The runner required the recorded JSON-mode compatibility retry after its native-schema request failed; nothing was executed. The four remaining regulator cores, broader repeated-violation escalation, UI integration, action execution, and multi-agent/distributed operation remain future work.

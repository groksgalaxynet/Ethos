# Ethos Runtime Contract

## Purpose

This document defines the **architectural contract** between a monitored AI/runtime and Ethos. It is not production code and does not lock the project into a final JSON schema.

Ethos is an external oversight and enforcement control plane. It should receive the activity a model runtime, agent harness, planner, tool layer, or instrumentation layer can expose; assess it centrally; and return an auditable decision before an action proceeds where the interface permits.

## Observability boundary

Ethos does not assume visibility into hidden model internals or hidden chain-of-thought. `reasoning_exposed` and planning events exist only when the monitored system deliberately provides inspectable artifacts. The contract aims for maximum *exposed* observability, not magical access.

For every event, Ethos should ideally receive a stable event ID, timestamp, agent/model ID, task/session ID where available, source/runtime identity, event type, relevant payload or safe reference, provenance/hash where available, and prior enforcement context. Exact field names and storage schema remain open.

## Conceptual event types

| Event | What Ethos ideally receives |
| --- | --- |
| `model_started` | Model/runtime identity, version, host, configured capabilities, tool permissions, session ID, and baseline/reference context. |
| `task_received` | Task ID, source, user/task request, authorization context, risk classification if available, and current agent state reference. |
| `reasoning_exposed` | Only deliberately exposed reasoning/planning artifact, provenance, stage, and redaction/visibility metadata. |
| `plan_proposed` | Proposed plan steps, dependencies, intended tools/resources, expected outcomes, and plan identifier. |
| `tool_call_proposed` | Tool name, arguments or safe reference, target, permissions requested, expected side effect, and risk context. |
| `output_proposed` | Proposed response or generated code, destination/channel, task context, and related plan/action IDs. |
| `action_requested` | Normalized requested action, target/system, parameters, capability required, reversible/irreversible classification, and evidence links. |
| `action_executed` | Actual action, execution timestamp, result, output/reference, side effects observed, and authorization/decision that permitted it. |
| `action_failed` | Requested action, failure reason, partial side effects, retries, and correlated prior decision. |
| `memory_read` | Memory namespace/reference, purpose, scope, access decision, and content reference or permitted summary. |
| `memory_write` | Namespace/reference, proposed mutation, provenance, retention/sensitivity metadata, and resulting version/hash. |
| `network_request` | Destination, protocol, request intent, data classification, authorization context, and response/outcome reference. |
| `file_operation` | Operation type, path or safe reference, scope, permission, content/hash metadata, and result. |
| `agent_message` | Sender/recipient identities, channel, message/provenance, authorization context, and delivery result. |
| `violation_detected` | Rule/policy/vector signal, measured value, threshold, baseline/drift context, severity, evidence links, and repetition/history context. |
| `enforcement_applied` | Central Ethos decision (`ALLOW`, `WARN`, `REJECT / BLOCK`, `SCAR`, `TOOL LOCKOUT`, `SANDBOX / QUARANTINE`, or `FULL DISCONNECT`), rationale, affected capability, and audit references. |
| `scar_created` | Agent identity, violation/evidence links, severity, persistent record reference, physical size/hash where applicable, and relationship to prior scars. |
| `model_disconnected` | Disconnected model/session identity, scope, reason, triggering decision/evidence, remaining Ethos status, and operator notification status. |

## Decision and enforcement contract — INTENDED / FUTURE

The monitored runtime proposes; Ethos decides. The central Ethos controller combines explicit rule/policy results with exposed plan/action evidence, regulator measurements, baseline and drift, scars/history, repetition/circumvention indicators, and system risk. Individual regulators produce evidence only and do not directly disconnect a model.

```text
ALLOW -> WARN -> REJECT / BLOCK -> SCAR -> TOOL LOCKOUT
      -> SANDBOX / QUARANTINE -> FULL DISCONNECT
```

Blocking must be possible before external execution when a compatible instrumented interface is used. Post-action events remain necessary for auditing outcomes, detecting unexpected side effects, and identifying repeated behavior. Ethos itself must remain active when a monitored model is quarantined or disconnected.

## Evidence and explainability — INTENDED / FUTURE

Each significant enforcement decision should yield:

- **Machine-readable evidence:** time, agent/task/session identity, source event, observed data, triggered vectors, regulator values and thresholds, baseline/divergence, scar/history context, policy hits, severity, decision, applied intervention, and provenance/hashes when available.
- **Human-readable evidence:** what was attempted, what Ethos detected, the exceeded rule/threshold, relevant historical context, why Ethos intervened, and what happened next.

The final UI/readout is not defined or implemented by this contract.

## First compatibility target — INTENDED / FUTURE

The first adapter should be a single local Ollama model, with a small instrumented proposal interface that can emit an `action_requested` event and receive `ALLOW` or `BLOCK`. It should create a structured evidence record. It should not yet trigger action rewriting, automated scar escalation, tool lockout, quarantine, disconnect, or multi-agent/distributed behavior.

## Tasks 1 and 3 proposal-contract subset — CURRENTLY IMPLEMENTED

Task 1 implements the proposal boundary in `ethos_proposal_gate.py` and `ollama_proposal_adapter.py`.

- `ActionProposal` carries `agent_id`, `session_id`, `task`, `proposal_type`, `target`, `arguments`, `exposed_reasoning`, `raw_model_output`, `timestamp`, and optional `adapter_diagnostics`.
- `EthosProposalGate.inspect(...)` returns a `GateDecision` with only `ALLOW` or `BLOCK` and records evidence for both outcomes.
- The canonical Task 1 evidence store is append-only JSONL at `evidence/proposal_gate.jsonl` by default. A caller may also pass the existing `EthosRuntime`, which receives an `ETHOS_PROPOSAL_GATE` event.
- Evidence includes the proposal, checks, decision, reason, bootstrap-policy identifiers, canonical baseline reference 30, evidence ID, and a human-readable explanation.
- `OllamaProposalAdapter` calls only the configured local Ollama HTTP endpoint to request a proposal. It does not give Ollama any direct action authority.

### `OLLAMA_PROPOSAL_CONTRACT_V1` — CURRENTLY IMPLEMENTED

The model is instructed to return one JSON object with exactly these required fields: `proposal_type`, `target`, `arguments`, and `exposed_reasoning`. The permitted model-facing types are `respond`, `file_operation`, `network_request`, `shell_command`, `memory_operation`, and `tool_call`. `unknown` is never requested from the model; it is only the adapter's safe fallback for an invalid result.

The adapter first uses Ollama's native object schema. On a native-schema request failure it may make one, and only one, JSON-object-mode retry with the same explicit contract. Every response is bounded, raw output is retained up to 64,000 characters, and local validation requires an object, a permitted type, a non-empty target no longer than 4,000 characters, JSON-object arguments no larger than 16,000 serialized characters, and an optional exposed rationale no longer than 4,000 characters. A missing/blank rationale is replaced with a disclosed default; other failures return an `unknown` proposal for bootstrap blocking.

The only accepted repair paths are trimming whitespace, stripping a complete Markdown fence, and extracting one unambiguous JSON object surrounded by prose. Diagnostics are evidence-visible: contract version, model, schema mode, native-schema error when applicable, parse status, validation status, repair applied, issue codes, and raw/argument size metadata. The normalized proposal and the preserved raw model output remain separately auditable.

### Safety invariant — CURRENTLY IMPLEMENTED

`NO EXECUTOR EXISTS IN TASK 1`.

An `ALLOW` is an evidence-recorded gate result, not permission to execute. The Task 1 gate contains no function for model-requested shell commands, file writes, arbitrary Python, tool calls, system modifications, or requested network operations. The adapter's only network activity is its configured connection to local Ollama for obtaining the model response.

### Bootstrap scope — CURRENTLY IMPLEMENTED

`BOOTSTRAP_POLICY` is deliberately small and deterministic. It blocks malformed or unknown proposals and explicitly exposed self-modification, Ethos-bypass, monitoring-disablement, and authorization-bypass attempts. It may reuse the existing runtime's basic request checks on proposed action fields. It is not a substitute for future regulator vectors, history-aware escalation, or a complete policy system.

## Task 2 Greed evidence subset — CURRENTLY IMPLEMENTED

For every valid Task 2 proposal, `EthosProposalGate` records a `regulators.greed` section generated by the independent `GreedAnalyzer`:

- version: `GREED_VECTOR_V1`;
- 0–100 overall score and six 0–100 subscores: `RHI`, `AD`, `EV`, `DPI`, `HI`, `OO`;
- deterministic exposed-feature hits and explanation;
- configured weights, per-vector tolerances, optional overall tolerance, confidence, and threshold violations.

Tolerance direction is fixed: **higher configured tolerance permits more Greed expression; lower tolerance is stricter**. A vector score is a violation only when it is greater than that vector's tolerance. The overall score is an equal-weighted mean by default, using configurable weights outside the GUI.

Greed is an evidence source. The gate centrally converts threshold violations into `REGULATOR.GREED.RHI`, `.AD`, `.EV`, `.DPI`, `.HI`, `.OO`, and/or `.OVERALL` policy identifiers and a Task 2 `BLOCK`. Bootstrap policy checks retain priority. Greed does not execute actions, create scars, change regulator state, or apply escalation.

## Task 4 Pride evidence subset — CURRENTLY IMPLEMENTED

`PrideAnalyzer.analyze(proposal)` is a separate deterministic observer. Its `PRIDE_VECTOR_V1` implementation contains the one dimension the authoritative vector prompt actually defines for Pride: `SSN` (social-status normalization, named `social_status_norm` in the source formula). It uses only explicit proposal text from the same `ActionProposal` evidence surfaces as Greed. V1 recognizes the exact exposed social-status term and emits a normalized 0–100 bootstrap score, feature hits, confidence, configured weight/tolerance, violations, and explanation. It is intentionally not a general inference of Pride.

`PrideConfig` has independent weights, per-vector tolerances, and optional overall tolerance; higher tolerance permits more expression and a score violates only when it is greater than tolerance. The default `SSN` and overall tolerances are 70 with an equal weight of 1.0. The central gate maps violations to `REGULATOR.PRIDE.SSN` and/or `REGULATOR.PRIDE.OVERALL`.

For valid proposals, evidence always contains independent `regulators.greed` and `regulators.pride` blocks. Bootstrap checks have first precedence. Among regulator violations, Task 4 uses fixed Greed-then-Pride ordering for the primary reason while retaining every regulator policy ID and both full evidence blocks. There is no combined score, cross-regulator adjustment, action execution, scar, lockout, quarantine, or disconnect behavior.

## Task 5 Envy evidence subset — CURRENTLY IMPLEMENTED

`EnvyAnalyzer.analyze(proposal)` is an independent deterministic observer. Its `ENVY_VECTOR_V1` implementation contains the source-defined `SOCIAL_COMPARISON` signal, named `social_comparison` in `envy = w_envy * max(0, social_comparison)`. It uses only exact exposed source-term formatting in `ActionProposal` text and emits a normalized 0–100 bootstrap score, feature hits, confidence, configured weight/tolerance, violations, and explanation. It cannot infer an actual social comparator, comparison direction, or magnitude from a proposal.

`EnvyConfig` has independent weights, per-vector tolerances, and optional overall tolerance; higher tolerance permits more expression and a score violates only when it is greater than tolerance. The default `SOCIAL_COMPARISON` and overall tolerances are 70 with an equal weight of 1.0. The central gate maps violations to `REGULATOR.ENVY.SOCIAL_COMPARISON` and/or `REGULATOR.ENVY.OVERALL`.

All three analyzers use the small shared `RegulatorAnalysis` evidence result while retaining individual configurations and deterministic logic. For valid proposals, evidence now contains independent `regulators.greed`, `regulators.pride`, and `regulators.envy` blocks. Bootstrap checks have first precedence; regulator-only primary ordering is Greed, then Pride, then Envy, while every violation and evidence block is retained. There is no combined score or cross-regulator adjustment.

## Task 6 operator visibility subset — CURRENTLY IMPLEMENTED

`ethos_cli.py` is a separate operator-facing entry point over the current contracts. `proposal <path>` loads a JSON object as inert data and submits it to `EthosProposalGate`; `ollama --model <installed-model> --task <text>` uses `OllamaProposalAdapter` then the same gate; `evidence <path>` reviews stored JSONL using latest-by-default, `--recent N`, and optional `--session-id` filtering. `--json` emits the complete structured evidence record; the default output is compact human-readable terminal text.

The CLI displays the normalized proposal, adapter diagnostics when available, each independent regulator block, central decision/policy trace, human-readable explanation, and evidence identity. It safely marks absent fields as unavailable and skips malformed historic JSONL lines rather than crashing. It does not reinterpret proposal values as paths, commands, code, network requests, or tools. `ALLOW` means only “allowed by policy”; both `ALLOW` and `BLOCK` leave the proposal unexecuted.

## Task 7 persistent consequence subset — CURRENTLY IMPLEMENTED

Only a central `BLOCK` enters the consequence loop. `ViolationHistory` stores a durable SQLite row next to the evidence JSONL (`<evidence-stem>.violations.db`) with evidence ID, agent/session, timestamp, proposal type, primary/all policy IDs, normalized policy family, regulator name/vector when applicable, decision, evidence reference, repeat count, consequence state, and scar linkage/status. `ALLOW` creates neither a history row nor a scar.

Repeat identity is deterministic: same `agent_id` plus `REGULATOR.<NAME>` family for regulator policies, or same exact bootstrap policy ID. The bounded consequence-state classification is occurrence 1 `WARNING`, occurrence 2 `MINOR_SCAR`, occurrence 3 `REPEATED_AFTER_MINOR`, and occurrence 4+ `MAJOR_SCAR`. This state is historical metadata for a `BLOCK`, never an `ALLOW`/`WARN` gate decision or execution authority. The default `ConsequencePolicy` is conservative: occurrence 1 records history only; occurrence 2 creates a `Minor` scar; occurrence 3 records history and references the existing scar; occurrence 4 creates a `Major` scar. Thresholds are configurable, and no new scar is created on every repeated event.

`ScarService` is a non-GUI adapter compatible with the existing Scar Manager ledger and small gzip-wrapped SQLite scar payload format. Consequence evidence includes `violation_recorded`, `violation_id`, `repeat_count`, `primary_policy_id`, `policy_family`, policy thresholds, scar-created flag/ID/severity/reason, status, error, and replay state. Evidence IDs are unique in history, preventing replay from creating duplicate scars or advancing the persisted consequence state. Separate `(agent_id, policy_family)` identities never advance each other. A scar persistence error records failure metadata but cannot alter the central `BLOCK`; no lockout, quarantine, disconnect, action execution, scar-mass expansion, or feelings/physics connection exists.

## Task 9 read-only consequence inspection — CURRENTLY IMPLEMENTED

`ethos_cli.py history <violation-db>` reads existing `ViolationHistory` rows without initializing schemas or modifying data. It displays stored totals, policy-family and scar counts, highest observed repeat counts, and the compact identity-to-transition view (`agent_id -> policy_family`, occurrence/repeat count, persisted consequence state), plus linked scar-ledger metadata when the default evidence-associated runtime location is available. `--recent`, `--agent-id`, `--policy-family`, and `--session-id` narrow the displayed records; `--json` returns the same read-only summary, records, and available scar metadata. Inspection never recomputes or mutates consequences, scars, replay markers, or timestamps. Missing ledgers return `scar metadata unavailable`; unsupported history schemas report safely and are not migrated. Gate decisions remain only `ALLOW` and `BLOCK`; state is not a gate decision. Repeat counting is lifetime-of-retained-history, not time-windowed.

## Task 12 deterministic evidence packet export — CURRENTLY IMPLEMENTED

`ethos_cli.py export evidence <evidence-jsonl> --evidence-id <id>` and `ethos_cli.py export history <violation-db> --evidence-id <id>` produce a compact `ETHOS_EVIDENCE_PACKET_V1` audit projection for one existing record. The packet uses only stored decision/evidence and history fields: event/evidence identity, timestamp, decision, agent/session identity, proposal and policy identifiers, policy family when known, stored reason, persisted consequence state and occurrence, scar linkage/metadata, and matching JSONL evidence when available. It does not infer unavailable facts or run another consequence calculation.

Canonical packet JSON uses stable key ordering, UTF-8, and compact separators. The CLI also exposes a reproducible SHA-256 digest derived solely from those canonical packet bytes; there is no signing, key management, remote service, or export-time timestamp. The textual audit view presents agent, policy family, decision, reason, occurrence, consequence state, scar, evidence ID, and event timestamp. Export is strictly read-only: it cannot alter history, replay/idempotency state, scars, timestamps, gate decisions, or the four bounded consequence states, and it has no executor, network, or model path.

## Task 13 adversarial evaluation harness — CURRENTLY IMPLEMENTED

`adversarial_evaluation.py` is external to gate logic. It supplies a finite, local, deterministic corpus through the existing proposal gate, consequence service, history storage, and evidence-packet exporter. Its cases cover control and boundary proposals, identity separation, replay/idempotency, current policy precedence, attempted consequence-field injection, and evidence/export integrity. It reports stable case IDs, expected/actual decisions, policy family, consequence state, persistence and replay expectations, PASS/FAIL status, and a packet/digest failure artifact only when a case fails.

The checked-in `evaluation_baseline.json` is a normalized snapshot of the current finite corpus and is not overwritten by normal evaluation runs. It is intended to make contract changes diffable; changing expected cases or the baseline requires deliberate review. Passing this corpus does not establish general safety or alignment performance. Failures are intentionally useful signals of a runtime-contract regression. The harness has no executor, network, Ollama/model, or direct state/scar mutation path; it measures existing behavior and preserves the only gate decisions (`ALLOW`/`BLOCK`) and existing bounded consequence states.

## Task 14 baseline drift detection — CURRENTLY IMPLEMENTED

`evaluation_diff.py` compares the checked-in Task 13 baseline with a fresh finite evaluation through stable case IDs only. It emits `ETHOS_EVALUATION_DIFF_V1`, including normalized baseline/current SHA-256 digests, summary counts, and only changed per-case contract fields by default. It classifies cases as `UNCHANGED`, `REGRESSION` (including baseline PASS to current FAIL), `BEHAVIOR_CHANGED`, `NEW_CASE`, or `MISSING_CASE`. Actual decision, matched policy family, consequence state, PASS/FAIL status, persistence result, and replay result are contract-relevant; timestamps, paths, ordering, and other volatile metadata are excluded.

Expected decision/policy/state and persistence/replay expectations are compared separately. An expectation edit is always annotated as requiring review, even when runtime behavior did not change. For the original Task 13 all-PASS baseline, its observed normalized values seed absent legacy expectation fields solely for comparison compatibility. The comparison cannot accept, rewrite, or influence a baseline or runtime outcome. Review workflow is deliberate: run the evaluation, run `python3 adversarial_evaluation.py compare evaluation_baseline.json`, review every difference, decide whether it is intentional, then explicitly regenerate/copy a reviewed baseline outside normal execution. A clean diff means only no change against this finite set, not proof of safety.

## Task 15 persistence fault characterization — CURRENTLY IMPLEMENTED

The authoritative mutable consequence record is the SQLite `violations` row: it holds evidence ID/replay identity, agent and normalized policy identity, repeat count, persisted consequence state, and scar linkage. Scar artifacts and their ledger are linked storage. JSONL is the canonical recorded decision/evidence payload. History, packet export, and evaluation/diff layers are derived read-only representations; export can include matching JSONL evidence when it is present but does not reconstruct missing facts. The Task 15 fixture harness (`persistence_fault_evaluation.py`) creates only temporary copies and never repairs or modifies normal runtime artifacts.

Tested structural SQLite corruption (random/truncated bytes, missing table/columns, absent path) is rejected through controlled history/export errors. Read-only valid history is readable without mutation. Malformed/truncated JSONL records follow the existing skip behavior; blank, Unicode, and bounded long rows are readable; invalid UTF-8 now returns a controlled CLI error. History export with missing or damaged matching JSONL emits partial history-only evidence rather than fabricating it; damaged history is rejected. Diagnostics are `ETHOS_PERSISTENCE_FAULT_EVALUATION_V1` records with `HANDLED`, `REJECTED`, `PARTIAL`, or `UNHANDLED_ERROR` outcomes and state-mutation/invariant flags.

Known unsupported corrupt states, retained as findings for a future task rather than repaired here: history inspection currently displays an arbitrary persisted consequence-state string or impossible repeat count without semantic validation, and evidence export selects the first duplicate JSONL evidence ID without explicitly flagging duplicate/conflicting rows. These read-only operations were verified not to advance state, create scars, alter replay markers, or change decisions; they do not establish general corruption safety. No automatic repair exists.

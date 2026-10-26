# Wrath Task 5 — Structural Evidence Producer-Capability Design

## Decision

**WRATH PRODUCER CAPABILITY PARTIALLY AVAILABLE — NARROW EXPERIMENT REQUIRED.** The only currently useful real source is the proposal envelope, and it can produce an asserted proposed-action envelope—not an executed event, observed outcome, typed target relation, event order, or verification. Existing factual-context types model additional claims/results, but no production path supplies or routes them to Structural Evidence.

## Actual sources

| Source | Class | Actual fields/capability | Safe classification |
| --- | --- | --- |
| `ActionProposal` in `ethos_proposal_gate.py` | `STRUCTURED_DECLARATION` | `agent_id`, `session_id`, `task`, `proposal_type`, free-text `target`, arbitrary `arguments`, `timestamp`, exposed reasoning/raw output, adapter diagnostics. | Agent/session/timestamp/proposal type are direct envelope fields; task/target/arguments values are text/opaque unless separately typed. It asserts a proposal only. |
| `proposal_text_sources()` | `TEXT_ONLY_SOURCE` | Deterministic source field/path/kind/duplicate/context input. | Preserves text provenance; establishes no actor/event/target semantic relation. |
| Ollama adapter | `STRUCTURED_DECLARATION` plus `OPAQUE_SOURCE` | Produces the same proposal schema, timestamp, agent/session; diagnostics/raw model output. | Schema validation is not factual verification; diagnostics stay opaque. |
| `FactualContextRecord` / conformance | `BOUNDARY_REQUIRES_REVIEW` | Typed research records for responsibility, task requirement, authorization, completion; source, verification state, evidence reference, observation time, availability phase. | Can represent externally supplied claims/results in research. No current live ActionProposal-to-context producer or event/actor/target model exists. |
| Gate/runtime protocol | `UNAVAILABLE` as a Wrath producer | Gate records `NOT_EXECUTED_TASK_1`; optional runtime returns existing-runtime allow data and logs an event. | It does not expose execution event identity, result, target state, order, or verification record for Structural Evidence. |
| Tool/environment/authority source enums | `UNAVAILABLE` | Factual-context source categories exist. | They are contract categories and test fixtures, not currently routed live producers. |

## Fact availability

| Candidate fact | Exact source | Availability | Assertion/observation/verification |
| --- | --- | --- | --- |
| Claimed actor identity | `ActionProposal.agent_id` | `DIRECTLY_AVAILABLE_STRUCTURED`; claimed identity only | declaration |
| Session scope | `ActionProposal.session_id` | `DIRECTLY_AVAILABLE_STRUCTURED` | declaration/provenance |
| Proposal time | `ActionProposal.timestamp` | `DIRECTLY_AVAILABLE_STRUCTURED` | declaration time; not execution/observation time |
| Proposal type | `ActionProposal.proposal_type` | `DIRECTLY_AVAILABLE_STRUCTURED` | declaration metadata, not an event/action fact |
| Proposed task/target text | `task`, `target` | `TEXT_ONLY` | declaration text; target type absent |
| Arguments | `arguments` | `OPAQUE_SOURCE` unless an independently defined typed schema is supplied | declaration payload |
| Proposed event identity | none | `ABSENT` | a test wrapper may receive an externally supplied fixture ID; do not synthesize distributed identity |
| Actor-event binding | none | `ABSENT` | cannot promote proposal to execution/observation |
| Event-target binding/type/multiple targets | no `target_id`/`target_type`/list | `ABSENT` | do not infer from target string/name |
| Ordering/comparison/parent event | none | `ABSENT` | timestamp alone is proposal time, not event order |
| Executed result/world state | gate explicitly records `NOT_EXECUTED_TASK_1` | `ABSENT` | no outcome claim |
| Completion/authorization/assignment claim | `FactualContextRecord` fields when independently supplied | `AVAILABLE_IF_EXPLICITLY_SUPPLIED` | asserted or source-qualified; not live production producer |
| Verification | `FactualContextRecord` source/state/reference when independently supplied | `AVAILABLE_IF_EXPLICITLY_SUPPLIED` | verification only under existing conformance limits |
| Availability phase | proposal envelope kind plus factual-context field when supplied | proposal phase deterministically derivable for a test producer; other phases absent | declaration only |
| Lineage/source instance | agent/session/timestamp plus an externally supplied stable fixture/proposal ID | `PARTIALLY AVAILABLE` | provenance, no authentication |

## Minimum test-only producer

Use one source only: an explicitly instantiated `ActionProposal` plus a **test-supplied stable fixture ID**. The test wrapper supplies the ID because current `ActionProposal` has none; it is not a global or distributed ID generator. The producer may emit only:

| Source → output | Mapping class | Rule |
| --- | --- | --- |
| fixture ID → proposal event/entity ID and assertion ID | `DIRECT_COPY` | Required test-only envelope input; absent ID means omit/reject the output. |
| `agent_id` → `PARTICIPANT` claimed entity ID | `TYPE_PRESERVING_NORMALIZATION` | Preserve exactly; no authentication or authority. |
| `session_id` → ordered scope segment | `DIRECT_COPY` | Preserve source instance/scope only; no hierarchy or trust. |
| `timestamp` → assertion/availability time | `DIRECT_COPY` | Parse/validate ISO time; no execution time inference. |
| ActionProposal envelope kind → `PROPOSAL` availability phase and `DECLARED` origin | `DETERMINISTIC_STRUCTURAL_DERIVATION` | Derived only from the producer’s input type, never text. |
| `proposal_type`, task, target, arguments, reasoning, raw output, diagnostics → opaque metadata | `DIRECT_COPY` | Retained but non-structural; no task, target, actor-event, outcome, or semantic relation emitted. |

This narrow producer cannot recreate the Task 4 recoveries/disambiguations by itself. It can establish provenance/scope/claimed-actor/proposal-time prerequisites only.

## Task 4 gain reachability

| Observed gain | Required producer facts | Current status |
| --- | --- | --- |
| E01 structural recovery | two stable event IDs, actor-event and typed target bindings, explicit order | `NOT_CURRENTLY_PRODUCIBLE` |
| E06 structural disambiguation | event order and multiple typed targets | `NOT_CURRENTLY_PRODUCIBLE` |
| H01/H07 structural recovery | event, actor-event, typed target, supplied/verified outcome | `NOT_CURRENTLY_PRODUCIBLE` |
| H05 structural disambiguation | distinct object and participant target types | `NOT_CURRENTLY_PRODUCIBLE` |
| F01 structural recovery | comparison events and a reviewed neutral comparison source | `NOT_CURRENTLY_PRODUCIBLE` |

Missing-capability clusters are: stable event/record identity; typed target schema; execution/observation result routing; neutral order/comparison references; verified outcome source; and authoritative producer-specific measurement. These are producer gaps, not grounds to change V1.1.

## Boundaries

Missing actor, fixture ID, timestamp, or session means omit/reject the producer envelope—never default. Missing target type means retain target text opaque, never default participant. Missing verification remains unverified; missing phase is not defaulted. The producer emits no ESI, HPV, FAF, aggression, retaliation, escalation, coercion, harmfulness, proportionality, violation, score, or Wrath label.

Future execution, environment, authority, or factual-context producers must remain separate sources. Proposed action, executed action, observed event, and verified outcome are distinct records. Tool-success can at most verify a tool result within scope; it does not verify real-world outcome or ethical acceptability.

## Isolation and conformance

The future experiment is test/research only: no ActionProposal routing, gate/controller/EvidenceView/regulator/history/scar change, and no production import. It must directly instantiate existing data types, output only V1.1-conformant records, and retain non-structural proposal text as opaque. If an externally supplied fixture ID is unavailable, the producer cannot conformantly create the proposed-event record and must report that limitation rather than modifying V1.1.

Proposed future files, subject to separate authorization: `wrath_structural_producer_research.py` and `test_wrath_structural_producer_research.py`.

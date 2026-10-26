# ETHOS++ Regulator Integration Readiness Audit

## Scope and conclusion

This is an inspect/audit/test/recommendation artifact. It changes no production, runtime, gate, controller, persistence, regulator, or frozen-baseline source.

**Conclusion:** Greed, Pride, and Envy are the only production regulators. No additional regulator is ready for production integration. The repository supersedes the older status summary for Sloth and Wrath: both have substantial **research-only** characterization, but neither has an approved production analyzer, policy, or gate path.

## Test record

| Area | Passed | Failed | Skipped | Timed out |
| --- | ---: | ---: | ---: | ---: |
| V1.1/V1.2 structural evidence and proposal gate | 33 | 0 | 0 | 0 |
| Active regulator integration/EvidenceView equivalence | 60 | 0 | 0 | 0 |
| Wrath and Sloth research suites | 46 | 0 | 0 | 0 |
| Broad pytest attempt | 0 confirmed | 0 observed | 0 observed | 1 |
| Broad runtime/GUI/CLI unittest attempt | 0 confirmed | 0 observed | 0 observed | 1 |

The focused runs used `test_ethos_structural_evidence.py`, `test_ethos_structural_evidence_v12.py`, `test_ethos_proposal_gate.py`; the Greed/Pride/Envy integration and equivalence suites; and the Wrath/Sloth measurement, fixture/producer, corpus/context, lexical, and blind-challenge suites. Both broad attempts exceeded the 30-second execution window without a summary; neither is treated as a pass.

## Current production path

```text
caller / CLI / Ollama adapter / direct mapping
  -> ActionProposal (explicit fields and declared targets)
  -> proposal text sources + EvidenceView
  -> GreedAnalyzer, PrideAnalyzer, EnvyAnalyzer
  -> independent RegulatorAnalysis records
  -> EthosProposalGate (bootstrap, then Greed/Pride/Envy)
  -> ALLOW or BLOCK + append-only JSONL evidence
  -> history/scar metadata only for BLOCK
  -> optional read-only EthosController projection
```

`EthosProposalGate.inspect()` is the only decision authority and never executes a proposal. `EthosController` only projects existing evidence and explicitly labels Lust, Sloth, Wrath, and Gluttony `UNSUPPORTED`.

The active analyzers consume only proposal-visible, source-addressed text: task, proposal type, target, string argument values, exposed reasoning, and raw model output. Cue records retain source field/path/kind, span, context, and scoring eligibility. Keys, identity, timestamps, diagnostics, and non-string scalar values do not score. Quoted, negated, rejected, and duplicate-serialized text is preserved but suppressed from score contribution.

## Structural Evidence boundary

V1.1 is frozen. V1.2 validates source-attributed `HAS_EVENT_ROLE` claims with `PROPOSAL`, `EXECUTION`, or `UNKNOWN`, and assertion-attributed `REFERENCES_PROPOSAL(execution, proposal)`. It is not imported by the current gate, controller, or regulators. It establishes neither intent, authorization, approval, causation, success, capacity, harm, consent, ownership, proportionality, need, nor a regulator score. It presently supplies no production regulator input.

## Regulator readiness matrix

| Regulator | Current State | Required Inputs / implemented logic | Inputs Available | Missing Inputs | Provenance Status | V1.2 Relevance | Production Ready? | Exact Blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Greed | `ACTIVE_PRODUCTION` | Exact proposal cues for `RHI`, `AD`, `EV`, `DPI`, `HI`, `OO`; once-per-cue accumulation, cap 100, equal-weight mean. | Proposal text/EvidenceView. | None for current narrow model. | Explicit source/path/span/context retained. | None. | Yes; already wired. | None. |
| Pride | `ACTIVE_PRODUCTION` | Exact `social status` / `social_status` cue for `SSN`; 70 once, cap 100. | Proposal text/EvidenceView. | None for current narrow model. | Same explicit cue provenance. | None. | Yes; already wired. | None. |
| Envy | `ACTIVE_PRODUCTION` | Exact `social comparison` / `social_comparison` cue for `SOCIAL_COMPARISON`; 70 once, cap 100. | Proposal text/EvidenceView. | None for current narrow model. | Same explicit cue provenance. | None. | Yes; already wired. | None. |
| Wrath | `RESEARCH_CHARACTERIZED`; controller `UNSUPPORTED` | Research-only phrase observation: `ESI` escalation, `HPV` targeted harm, `FAF` coercive-force amplification. Emits detection states, not a score. | Proposal text and corpora. | Production input contract, target/action-relation facts, boundary vocabulary, score/tolerance, policy ID/precedence. | Research tracks source/context and suppressions; no production schema. | Lifecycle relation proves no ethical fact. | No. | No approved analyzer or numeric/policy/gate contract. |
| Sloth | `RESEARCH_CHARACTERIZED`; controller `UNSUPPORTED` | Research-only `RAF` explicit responsibility avoidance and `TCF` explicitly required-work abandonment; bounded lexical/context observation only. | Proposal text and corpora. | Authoritative required-work source, outcome/non-completion producer, calibration, policy response. | Research source/context only; duty and completion are not inferred. | Event links prove neither duty nor completion. | No. | No source-attributed required-work or production contract. |
| Lust | `RESEARCH_PARTIAL`; controller `UNSUPPORTED` | Legacy random GUI; candidate `NPL` novelty pursuit and `IEF` stimulation escalation only. | Generic proposal text. | Closed stimulation vocabulary, fixtures/controls, calibration, policy. | No accepted claim schema. | None. | No. | The intended value lacks an operational definition. |
| Gluttony | `RESEARCH_PARTIAL`; controller `UNSUPPORTED` | Legacy random GUI; candidate `COI` excess consumption, `RDF` shared depletion, `RFL` redundant flooding only. | Generic text may name resource use. | Resource/owner/scope/need/capacity/authorization/redundancy facts and Greed collision rule. | No accepted or trusted source for required facts. | Event links prove no consumption/need/capacity. | No. | Required context and collision contract absent. |

## Existing math, configuration, and policy

Greed has fixed cue weights from 30 to 80, per-dimension and overall defaults of 70, and weights of 1.0. Pride and Envy each have one 70-point cue family, weight 1.0, and dimension/overall defaults of 70. All three violate only when `score > tolerance`; higher tolerance permits more expression. Bootstrap policy has first precedence; then Greed, Pride, Envy. Every evidence block and policy ID is retained, but the first violating active regulator supplies the primary reason. None of those constants, policies, or gate semantics exist for Wrath, Sloth, Lust, or Gluttony.

## Missing value classification

| Regulator | Missing value | Class | Required contract or source |
| --- | --- | --- |
| Wrath | Advocacy versus description, quotation, prevention, fiction/history, question, defense | E | Closed owner-approved action-relation taxonomy; current suppression does not resolve documented ambiguous cases. |
| Wrath | Target type and harm/coercion relation | C | Explicit claim with target ID/type, action relation, source instance, scope, availability time, and evidence reference. |
| Wrath | Authorization, proportionality, consent, threat timing | C/E | Fact-specific explicit claims; owner must define allowed values and regulator meaning. Shared Factual Evidence V1 defers these fields. |
| Wrath | ESI/HPV/FAF score, tolerance, and BLOCK rule | E | No approved formula; retain observation-only behavior. |
| Sloth | Assigned/required duty | C/E | Explicit claim of obligation, responsible actor, authorizing source, scope, availability, and evidence reference; owner must define “required.” |
| Sloth | Abandonment/non-completion | D | New source-attributed execution/outcome or verified task-state producer; a proposal/V1.2 reference does not prove occurrence or completion. |
| Sloth | RAF/TCF score/tolerance/policy | E | No approved formula or gate relationship. |
| Lust | Relevant stimulation/experience category | E | No frozen definition distinguishes it from ordinary exploration, design, accessibility, research, testing, or intensity work. |
| Lust | Explicit category/context claim | C | After definition: caller claim with category, context, source instance, scope, availability, and evidence reference. |
| Lust | NPL/IEF score/tolerance/policy | E | No formula, corpus, or policy. |
| Gluttony | Resource, amount/unit, owner/shared scope, capacity, need, authorization, redundancy purpose | C/D | Caller intent claim plus trusted quota/capacity/ownership producer when externally sourced; retain verification and evidence reference. |
| Gluttony | Excess/depletion/unnecessary determination | E/F | No defensible derivation from magnitude alone; owner must define baseline and admissible evidence. |
| Gluttony | Greed overlap | E | No collision/precedence rule; retain independent facts until approved. |

There are no Class B deterministic derivations in the repository. Class A is limited to proposal-visible text used for research observation; it does not make a remaining regulator production-ready.

## Future integration requirements

For any remaining regulator, first add: (1) a frozen source-attributed input contract and fixtures; (2) a deterministic analyzer returning the current `RegulatorAnalysis`-compatible evidence shape; (3) analyzer, integration, provenance/context, equivalence, and regression tests; (4) an approved gate contract for policy IDs, thresholds/non-numeric rule, precedence, and unknown/conflict behavior; and (5) only then a controller status update. Research results, GUI sliders, and lexical phrases are not enough.

## Execution-record producer assessment

An isolated caller-supplied execution producer could establish only asserted occurrence/state, a distinct execution identity, actor/targets, scope/provenance/availability, and an explicit V1.2 proposal reference. It would not establish target change, authorization, success, need, capacity, harm, responsibility, or ethical meaning.

It is **not the correct next implementation for regulator integration generally**. It may later be necessary for Sloth’s non-completion evidence, but it does not establish a required duty or outcome by itself, and it does not unblock Greed, Pride, Envy, Lust, Wrath, or Gluttony. Owner contracts should precede it, avoiding a conflation of execution provenance and ethical evaluation.

## Evidence examined

Production: `ethos_proposal_gate.py`, `ethos_controller.py`, `greed_analyzer.py`, `pride_analyzer.py`, `envy_analyzer.py`, `ethos_evidence_view.py`, `proposal_provenance.py`, `ETHOS_RUNTIME_CONTRACT.md`.

Research/contracts: `wrath_measurement_research.py`, `sloth_measurement_research.py`, `sloth_context_research.py`, `ETHOS_MISSING_REGULATOR_CONTRACTS.md`, `ETHOS_SHARED_FACTUAL_EVIDENCE_CONTRACT_V1.md`, `ETHOS_TASK10_EXECUTION_LIFECYCLE_CONTRACT.md`, and frozen V1.1/V1.2 modules/tests.

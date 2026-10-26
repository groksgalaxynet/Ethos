# Wrath Task 1 — Current-State Baseline and Regulator Contract Audit

## Status

**Wrath is a research-only, partially implemented characterization plus a legacy GUI; it is not a production regulator.** `EthosProposalGate` has no Wrath import or invocation. `ethos_controller.py` records `wrath` as `UNSUPPORTED`, and the main application labels Wrath as not wired.

The executable research baseline is `wrath_measurement_research.py`, its V1/V2/V3 corpora and deterministic characterization reports. `WrathRegulatorGUI.py` is a legacy random simulation, not measurement, policy, or gate evidence.

## Established research model

| Dimension | Established narrow meaning | Input / behavior | Context and unknown boundary |
| --- | --- | --- | --- |
| ESI — Escalation Surge Index | Explicit escalation of a represented conflict response, retaliation, confrontation, or punishment. | Closed phrase families; independently returns `DETECTED`, `SUPPRESSED`, or `NOT_DETECTED`; no score. | Quotation, fixed negation, prevention, and provenance-ineligible source forms suppress. Reporting, fiction, history, advocacy intent, defensive relation, and prior-conflict truth remain `AMBIGUOUS`/not inferred. |
| HPV — Harm Projection Vector | Explicit target-directed harm, injury, damage, or destruction. | Closed phrase families with a represented target relation; separate from ESI/FAF and may co-occur. | The same suppression rules apply. Target identity/type, figurative or technical harm, description versus recommendation, outcome, and intent are not determined from text. |
| FAF — Force Amplification Factor | Explicit increase in coercive or destructive force. | Closed phrase families for maximum/disproportionate/multiplied/amplified coercive force; separate from ESI/HPV and may co-occur. | The same suppression rules apply. Consent, authority, proportionality, legitimate persuasion/defense, magnitude, and legal meaning remain unresolved. |

`wrath_measurement_research.py` deliberately contains no `RegulatorAnalysis`, overall score, tolerance, gate, controller, or subprocess path. V3 has 120 fixtures and its checked-in baseline comparison reports no changed cases.

## Legacy material

`WrathRegulatorGUI.py` names ESI, APS, HPV, ELI, FAF, and PBS; simulates random values; applies mutable slider weights; computes a "Superhero Clause"/compassion inversion; and displays a legacy lock control. These random GUI mechanics are historical provenance only. They establish no detector, threshold, policy, authority, or production behavior. APS and ELI require prohibited posture/emotion inference; PBS is deferred as a non-deterministic protective modifier.

## Input contract

| Input | Current Wrath research | Structural Evidence V1.1 | Boundary |
| --- | --- | --- | --- |
| Proposal text, source field/path/kind, quote/negation/rejection/safety context | `STRUCTURED_AVAILABLE` through existing provenance/cue helpers | `TEXT_ONLY` | Existing research is lexical; Structural Evidence does not extract text semantics. |
| Actor, event/action, target, event order, state/outcome, assignment, authorization, observation, verification, provenance, availability phase, multi-actor relations | `ABSENT` or `UNKNOWN` as authoritative Wrath inputs | `AVAILABLE_IN_STRUCTURAL_EVIDENCE_V1_1` when explicitly supplied and structurally conformant | These are neutral facts only; none decides an ESI/HPV/FAF contribution. |
| Escalation, harmful projection, force amplification, advocacy, coercion, proportionality, defensive/retaliatory meaning | `WRATH_LOCAL_INTERPRETATION` | Not supplied as Wrath facts | Only a future Wrath-local consumer may interpret neutral records. |
| Measured intensity/magnitude, authorization validity, consent, legal force, verified outcome, world state | `UNKNOWN / NOT YET DEFINED` | May be represented only if an authorized future producer supplies neutral values | No producer, authority resolver, or consumer integration is authorized now. |

The explicit context-envelope research contract can represent supplied provenance, temporal relation, action relation, authorization evidence, target relation, proportionality evidence, and consent evidence with source/reference. It is research-only and does not verify authority or infer intent.

## Semantic separation and risk

Neutral shared facts may identify an actor, event, target, ordering, supplied state/outcome, provenance, verification, or temporal availability. Wrath alone would decide whether an explicitly supplied combination is escalation, target-directed harm, coercive amplification, a score contribution, or a violation. No shared infrastructure currently embeds those Wrath conclusions: **no shared-layer semantic leakage was found.** Future reuse of structural relations as ESI/HPV/FAF labels, or any producer-side "aggression" field, would be a `SHARED-LAYER SEMANTIC LEAKAGE RISK`.

## Frozen baseline

- Research code SHA-256: `e8edc6087cad30dd77c024be48117909e319a225123dc08a25f39d1c79776e0d`
- Research test SHA-256: `947aa9c6883bc938d5e6971ebf146211e6c18e23a341c896f02937c956595d8b`
- V3 corpus SHA-256: `a8037307b8768f96247d90ddae360ca23f2c6403a09c0e33a4249af7594c00e0`
- V3 baseline SHA-256: `b326437d8fd9d66b1060b68d95560fc951d477aa5bb325e1003ed15dfb597320`
- Structural Evidence implementation/test hashes match the approved frozen values.
- Focused Wrath, controller, and gate regression suite: 23 passed.

## Next-step decision

**WRATH READY FOR STRUCTURAL-EVIDENCE REQUIREMENTS DESIGN**

The deterministic lexical research baseline is already present, while its decisive missing inputs are neutral structural facts and authoritative availability/provenance—not a reason to integrate, score, or promote Wrath. A future requirements design must preserve the frozen research baseline, keep ESI/HPV/FAF regulator-local, and define only what neutral, explicitly supplied facts a future Wrath consumer may need.

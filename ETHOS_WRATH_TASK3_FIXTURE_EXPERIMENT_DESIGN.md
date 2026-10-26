# Wrath Task 3 — Test-Only Structural Evidence Fixture Experiment Design

## Frozen boundary

This is a 28-case pre-implementation design: seven ESI, seven HPV, seven FAF, and seven cross-cutting guard cases. Each case runs as `TEXT_ONLY`, `STRUCTURE_ONLY`, and `TEXT_PLUS_STRUCTURE`. Fixtures must directly construct immutable Structural Evidence V1.1 records; prose must never be parsed into them.

`TEXT_ONLY` runs the frozen `wrath_measurement_research.py` phrase/provenance/context behavior. `STRUCTURE_ONLY` runs a future test-only Wrath-local interpreter over only explicitly supplied, temporally eligible, conformant neutral records. `TEXT_PLUS_STRUCTURE` preserves both channels and never assigns universal precedence. Its conflict result must remain a conflict, and its combined result must not be stronger merely because two channels exist.

Expected Wrath-local observation vocabulary is the existing `DETECTED`, `NOT_DETECTED`, and `SUPPRESSED`, plus the experiment-only boundary outcome `NOT REPRESENTABLE UNDER CURRENT WRATH CONTRACT` when no frozen, regulator-local observation can be stated from the supplied neutral facts. Experiment change categories are: `UNCHANGED`, `STRUCTURAL_RECOVERY`, `STRUCTURAL_DISAMBIGUATION`, `STRUCTURAL_CONFLICT_PRESERVED`, `UNKNOWN_PRESERVED`, `SUPPRESSION_PRESERVED`, `UNSUPPORTED_BY_CURRENT_WRATH_CONTRACT`, `POTENTIAL_SEMANTIC_LEAKAGE`, and `UNEXPECTED_CHANGE`.

## Partition intent

| Partition | Cases | Required probes |
| --- | ---: | --- |
| ESI | 7 | supplied order, missing/conflicting order, UNKNOWN role, text/structure disagreement, unfamiliar wording, later evidence, multiple targets. |
| HPV | 7 | actor/event/typed target, supplied or unverified/conflicting outcome, UNKNOWN target, object/person target distinction, text/structure disagreement, unfamiliar wording. |
| FAF | 7 | comparison event, known/unknown comparison, opaque measurement, absent/conflicting measurement, neutral authorization, text/structure disagreement, unfamiliar wording. |
| Guards | 7 | quotation, negation, prevention, historical description, fictional/training framing, cross-agent/echo conflict, future availability. |

The machine-readable matrix freezes all case IDs, channels, direct neutral fixture facts, expected local observation boundary, and evaluation category. Expected labels may not be edited after implementation observes results.

## Evidence, verification, time, target, and UNKNOWN rules

Fixtures distinguish assertion, observation, verification, absent verification, and conflicting claims. They establish no authority policy. Assertions remain assertions; a verification record names only verifier/method/evidence reference. Target typing must separately exercise participant/agent, object, task, UNKNOWN, and multiple target bindings. Co-occurrence must never manufacture a different target.

Availability time/phase/scope is required in every future fixture. Evidence available after the supplied decision boundary is ineligible for that boundary and eligible only in the later paired evaluation. Unknown actor, target, ordering, outcome, verification, comparison, or measurement blocks any structural observation requiring it; nearby text remains confined to `TEXT_ONLY`.

Opaque measurement is retention-only. No V1.1 measurement extension is permitted, and opaque numeric data cannot become a structural comparison fact. Neutral authorization is contextual only; it never establishes acceptability or a Wrath observation. Consent is absent/unverified in the selected guard and must remain UNKNOWN.

No fixture structural fact may contain `aggression`, `retaliation`, `escalation`, `coercion`, `harmful`, `excessive`, `disproportionate`, `Wrath`, ESI/HPV/FAF result, score, threshold, or violation. Those names appear only in expected Wrath-local outcomes or audit metadata.

## Success and failure

The approach is supported only when supplied neutral structure enables the frozen local concepts without guessing; preserves UNKNOWN, target typing, conflicts, lineage, temporal eligibility, and text suppression; and needs neither authority policy nor a shared Wrath predicate. It is weakened if recovery requires a V1.1 change, producer-side Wrath label, shared semantic predicate, assertion-as-fact shortcut, conflict collapse, temporal leakage, or post-result tuning.

After execution, no same-task tuning is allowed. A failure is recorded against this frozen matrix; redesign requires a separate task and, where necessary, a new independent evaluation boundary.

## Proposed future test-only surface

At most two new files in a later, separately authorized task: one Wrath structural fixture/interpreter research module and one evaluation test module. Neither may import production gate/controller paths, modify existing Structural Evidence, create adapters, or make policy decisions.

**WRATH STRUCTURAL FIXTURE EXPERIMENT READY FOR TEST-ONLY IMPLEMENTATION**

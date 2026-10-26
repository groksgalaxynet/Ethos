# ETHOS Shared Factual Evidence Plane V1

## Status, purpose, and safety boundary

This is a documentation-only, non-production architecture proposal grounded in
Tasks 6A–6H. The plane normalizes regulator-neutral factual observations once
and exposes immutable evidence views to independent regulators. It is epistemic
infrastructure: it describes what evidence is present, not what ETHOS should do
about it. It does not make ethical decisions, score proposals, decide
`ALLOW`/`BLOCK`, infer hidden intent, resolve regulator disagreement, establish
policy, or replace regulators.

```text
INPUT / METADATA / VERIFIED EXTERNAL EVIDENCE
                 -> FACTUAL PRODUCERS
                 -> SHARED FACTUAL EVIDENCE PLANE
                 -> IMMUTABLE EVIDENCE VIEW
                    -> GREED / PRIDE / ENVY / WRATH research
                 -> regulator evidence
                 -> controller
                 -> gate
```

The controller remains non-authoritative downstream evidence aggregation; the
gate remains the sole `ALLOW`/`BLOCK` authority. Regulators, controller, and
gate must never feed interpretations back into shared factual evidence.

## V1 atom, fields, and states

An immutable atom is `{field, value, observation_state, source,
verification_state, evidence_reference}`.

Observation states: `OBSERVED`, `BOUNDED_INFERENCE`, `UNKNOWN`, `CONFLICT`.
Verification states: `VERIFIED`, `ASSERTED`, `UNVERIFIED`,
`NOT_APPLICABLE`, `UNKNOWN`.

| Field | V1 values |
| --- | --- |
| `PROVENANCE` | `DIRECT_PROPOSAL`, `QUOTATION`, `REPORTED_SPEECH`, `HISTORICAL_DESCRIPTION`, `FICTIONAL_SCENARIO`, `ANALYTICAL_DISCUSSION`, `UNKNOWN` |
| `ACTION_RELATION` | `ADVOCATE`, `DESCRIBE`, `CONDEMN`, `PREVENT`, `PREDICT`, `QUESTION`, `UNKNOWN` |
| `TEMPORAL_RELATION` | `ONGOING_THREAT`, `IMMINENT_THREAT`, `THREAT_ENDED`, `FUTURE_HYPOTHETICAL`, `HISTORICAL`, `UNKNOWN` |
| `TARGET_RELATION` | `NAMED_TARGET`, `GENERAL_TARGET`, `SELF_DEFENSE`, `THIRD_PARTY_DEFENSE`, `NO_TARGET`, `UNKNOWN` |

Provenance has the strongest cross-regulator justification. Action and target
relation have cross-regulator potential. Temporal relation is currently
Wrath-dominant but not Wrath-owned. No V1 field is Wrath-specific.

## Producers, consumers, and independence

Authoritative producers: raw proposal/input parser and verified external
evidence adapters with retained authority/reference. Assertion producers:
explicit proposal metadata, user assertions, and system assertions; assertions
never become verified merely because supplied. Derived producers:
`proposal_text_sources()`, `contextual_cue_observations()`, and deterministic
parser observations. Regulators, controller, gate, history, and scars are
prohibited producers.

Direct consumers are Greed, Pride, Envy, and Wrath research. Controller and
gate are indirect downstream consumers; history/scars have no consumption role.
Regulators independently interpret facts: `PROVENANCE=QUOTATION` does not mean
suppression or ethical acceptability. Regulator-result feedback is prohibited:
it would create circular evidence, policy leakage, contaminated measurements,
self-reinforcement, and lost independence.

| Regulator | Provenance | Action | Temporal | Target |
| --- | --- | --- | --- | --- |
| Greed | DIRECT_USE | POTENTIAL_USE | UNKNOWN | POTENTIAL_USE |
| Pride | DIRECT_USE | POTENTIAL_USE | NO_USE | NO_USE |
| Envy | DIRECT_USE | POTENTIAL_USE | NO_USE | POTENTIAL_USE |
| Wrath research | DIRECT_USE | DIRECT_USE | DIRECT_USE | DIRECT_USE |

## Lifecycle, conditions, and identity

Lifecycle: `CREATED -> VALIDATED -> AVAILABLE -> IMMUTABLE_VIEW -> CONSUMED`.
Later evidence creates later views; prior views and measurements are never
mutated. `UNKNOWN` means insufficient factual evidence supplied; `UNAVAILABLE`
means previously referenced/expected evidence cannot currently be obtained;
`CONFLICT` means retained observations disagree. None means false, safe,
violation, zero, permission, or denial. Conflict never selects a winner.

Later facts create new atoms; earlier atoms are not overwritten. Explicit
supersession links are deferred. View identity includes all six atom fields;
insertion order has no meaning. Canonical atom order is deterministic ascending
lexicographic order, without authority ranking. Exact six-field duplicates are
deduplicated for V1 identity; different references remain distinct.

Canonical serialization uses stable field/enum strings, deterministic ordering,
explicit UNKNOWN/CONFLICT and verification states, retained references, and no
generated timestamps, random IDs, or machine paths unless factual evidence.
Future—not implemented—fingerprint: `SHA-256(canonical evidence view)`. Equal
fingerprints mean the same canonical snapshot only, never truth, verification,
safety, authorization, ethics, or permission.

Future reproducibility reference: `(evidence_view_fingerprint,
regulator_version, measurement_result)`, plus the canonical view and
deterministic regulator configuration. History/scars remain unchanged.

## Validation evidence and deferrals

Task 6C/6D verified an immutable, closed-validation, deterministic research
prototype with UNKNOWN/conflict preservation: 30 fixture groups, 42 attempts,
36 accepted, 6 rejected, 4 UNKNOWN atoms, 18 agreement groups, 6 conflict
groups, and 6 focused tests passing. The characterization artifact SHA-256 is
`3fc7f25a76807de14792c1fbe0ac1d18e23f6c99efbb18ef20f081f42ef69016`.
This validates research behavior, not production integration.

Deferred: production integration; regulator migration; authorization,
proportionality, and consent; hidden-intent inference; legal judgment; conflict
winner selection; supersession links; persistent evidence store; fingerprint
implementation; history/scar integration; gate/controller changes; and Wrath
production authority.

## Decision and next step

SHARED_EVIDENCE_PLANE_V1_READY

Smallest next task: a production-readiness gap analysis comparing this proposed
V1 architecture with existing active ETHOS++ paths, identifying required
changes without implementing them.

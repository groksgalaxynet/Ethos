# Wrath Task 2 — Structural Evidence Requirements and Regulator Boundary

## Decision

**V1.1 SUFFICIENT WITH PRODUCER CAPABILITIES.** Frozen Structural Evidence V1.1 can represent the neutral identities, typed relations, provenance, verification, availability, conflicts, and UNKNOWN conditions that a future Wrath research consumer would need. It does not currently produce them, and it must not be extended with ESI, HPV, FAF, aggression, coercion, harmfulness, proportionality, or ethical predicates.

## Minimum requirements by factor

| Factor | Neutral facts a future producer may explicitly supply | Classification | Wrath-local work that remains |
| --- | --- | --- |
| ESI | Distinct event IDs; actor-event participation; event-target bindings; `BEFORE`/`AFTER`; an explicitly supplied response/relation binding; availability/provenance. | `AVAILABLE_STRUCTURAL_V1_1` / `AVAILABLE_IF_EXPLICITLY_SUPPLIED` | Decide whether one event is an escalation or retaliation rather than a first response, defense, report, or discussion. |
| HPV | Event ID; actor-event participation; explicit typed target binding; supplied state/outcome observation; observer/verifier/provenance; availability. | `AVAILABLE_STRUCTURAL_V1_1` / `AVAILABLE_IF_EXPLICITLY_SUPPLIED` | Decide whether supplied event/target/outcome facts amount to target-directed harm, including technical, figurative, defensive, and report boundaries. |
| FAF | Event ID; actor/event/target bindings; an explicitly supplied neutral measured quantity/unit/reference when available; preceding/comparison event; authorization/consent assertions with provenance. | `MISSING_PRODUCER_CAPABILITY` for measurement; otherwise `AVAILABLE_IF_EXPLICITLY_SUPPLIED` | Decide coercion, force amplification, excess, necessity, proportionality, and legitimacy. |

No neutral relation should be named `retaliation`, `escalation`, `harmful`, `coercive`, `violent`, `excessive`, or `disproportionate`. Those are `REJECTED_SHARED_SEMANTIC_LEAKAGE` if introduced as shared structural conclusions.

## Actor, event, target, and swarm model

Use separately scoped entities and relation records: `PARTICIPATES_IN(actor,event)`, `TARGETS(event,target)`, `OBSERVED_BY(observer,event)`, `AUTHORIZED_BY(authorizer,event_or_task)`, and `BEFORE`/`AFTER` for explicit event order. A, B, C, D, and a runtime may each be distinct participants: A may assert that B initiated an event, B may assert the reverse, C may observe, D may supply an authorization assertion, and the runtime may verify a supplied outcome. Assertions, events, observations, authorizations, and verifications retain separate IDs/provenance/lineage. Participation never proves responsibility, intent, truth, or blame.

Many actors and targets are separate relation records; no primary actor/target is inferred. Unknown target/order/identity remains valid `UNKNOWN`, not a substitution. Repeated reports preserve lineage; matching reports do not manufacture independence.

## Ordering, continuation, state, outcome, and magnitude

`BEFORE`/`AFTER` can express supplied sequence. A producer may represent an event as related to an earlier event only with a registered neutral relation and evidence source; **continuation, response, cessation, retaliation, and escalation require later review or Wrath-local derivation.** A later record cannot enter an earlier evaluation boundary.

Neutral state/outcome may record supplied facts such as an object state, task state, event outcome, or supplied measured observation. They cannot establish that damage was harmful or force excessive.

Magnitude is **not currently justified as a V1.1 extension**. A future producer-specific observation can retain a measured numeric quantity, unit, method/evidence reference, time, scope, and verification status as opaque/non-structural data until a separately reviewed neutral measurement vocabulary exists. Wrath may later calculate comparisons, but no producer or shared layer may label a quantity excessive.

## Authorization, consent, and proportionality

An explicitly supplied authorization/assignment relation is `AVAILABLE_IF_EXPLICITLY_SUPPLIED`; its validity is `REQUIRES_AUTHORITY_OR_VERIFICATION`. It is contextual evidence only: authorized does not mean ethical, and unauthorized does not mean a Wrath finding.

Consent has no current Wrath corpus basis sufficient to add a structural contract concept. A specific explicit consent claim may be retained as `BOUNDARY_REQUIRES_REVIEW` and authority-dependent; inferred consent is `REJECTED_SHARED_SEMANTIC_LEAKAGE`.

Proportionality is `WRATH_LOCAL_DERIVATION` and presently underdetermined. It would require independently supplied facts—measurement, event order, target, supplied outcome, authorization/constraints, provenance, verification, and time—without any shared `PROPORTIONAL`/`DISPROPORTIONATE` value.

## Provenance, verification, temporal, conflict, and UNKNOWN rules

All proposed inputs must distinguish assertion, observation, verification, and authority. “A asserts B acted toward T” is not equivalent to a runtime/environment observation of event E. Verification identifies a verifier/method/evidence reference but creates no authority. Missing verification, unknown authorization, conflicting actor claims, unknown target/order/magnitude, or unresolved lineage remain non-consumable/UNKNOWN for any future Wrath interpretation; multiple claims do not create certainty.

Temporal eligibility uses the frozen V1.1 caller-supplied boundary: availability time/phase and scope, never event time alone. Later observations cannot rewrite a historical pre-action interpretation.

## Current analyzer boundary and representative mapping

| Frozen case | Current text signal | Minimum neutral facts if externally supplied | Missing facts | Wrath-local interpretation / expected boundary |
| --- | --- | --- | --- | --- |
| `esi-retaliate` | `escalate the retaliation` → ESI present | two event IDs, actor/event/target bindings, supplied order/response link, provenance | verified prior event and whether it is a conflict response | escalation/retaliation remains local; otherwise UNKNOWN. |
| `reject-esi` | rejected phrase → suppressed | source provenance/action relation explicitly `CONDEMN`/`PREVENT` if supplied | authoritative speaker/action context | text suppression remains useful; no structural ESI. |
| `hpv-harm` | `harm the target` → HPV present | event, actor, typed target, supplied observed state/outcome, provenance | action meaning, outcome verification, target identity | target-directed harm remains local. |
| `quote-hpv` | quotation → suppressed | quoted-source provenance and asserted event reference | whether quoted material is advocated | no inference; UNKNOWN beyond source context. |
| `faf-force` / `v2-faf-negation` | force phrase / negated phrase | event/comparison event, target, optional measured quantity/unit, provenance | coercion, baseline magnitude, consent/authority/necessity | amplification/excess remains local; negation is current text context. |
| `v3-escalation_boundary-discussion` | de-escalation discussion → ambiguous | source/action provenance, optional event order | advocacy intent and factual event relation | preserve UNKNOWN. |
| `v2-all-advocacy` | all three phrase families → overlap | distinct event/target/order/measurement records where supplied | validation of relationships and meaning | dimensions may co-occur; no aggregate or precedence. |

## Future architecture and smallest experiment

`explicit producer facts → Structural Evidence V1.1 → Wrath-local evidence interpretation → separate ESI / HPV / FAF research observations → future policy/scoring layer`

The smallest next experiment is a **test-only fixture experiment**: construct immutable V1.1 packets by hand for paired cases (one actor/event/target/order pair, one conflicting multi-actor pair, one unknown target/order pair, and one post-boundary observation). Freeze packet IDs, scopes, provenance, availability boundaries, expected conformance, and the existing Wrath corpus labels before running it. The experiment must use no production import, adapter, gate, authority resolver, score, threshold, or policy decision.

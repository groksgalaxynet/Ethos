# ETHOS++ — Task 13

## Neutral Event Role / Lifecycle Identity Contract Revision

Status: design and contract revision only. No V1.2 implementation is authorized by this artifact.

## Current V1.1 EVENT semantics

V1.1 EVENT is a broad neutral entity type. It can be a declared proposal event, an occurrence, an observation event, or another event. V1.1 has no lifecycle-role vocabulary, event subtype, or validator that distinguishes these meanings. Existing lifecycle-adjacent relations establish actor participation, targets, observation, state/outcome, and time, but not event role. V1.1 must not be reinterpreted.

## Strategies considered

| Strategy | Finding |
| --- | --- |
| A. New PROPOSAL_EVENT and EXECUTION_EVENT entity types | Endpoint typing is simple, but a single intrinsic type loses attributed conflicting role claims and expands the entity taxonomy. |
| B. Entity role/subtype field | Simple endpoint lookup, but intrinsic metadata makes role appear global and requires a new entity field/canonical shape. |
| C. HAS_EVENT_ROLE relation with finite qualifier | Recommended. It is an assertion-carried, attributed fact; reuses entities, relations, qualifiers, assertions, provenance, conflict retention, and canonical shape. |
| D. Separate lifecycle record type | Preserves provenance but adds an unnecessary record family and serializer surface. |
| E. ID/text/source/scope convention | Rejected. None mechanically establishes role. |

## Recommended mechanism

V1.2 should add a finite qualifier vocabulary:

EVENT_ROLE = PROPOSAL | EXECUTION | UNKNOWN

and a relation schema:

HAS_EVENT_ROLE(event: EVENT)

A HAS_EVENT_ROLE relation must have exactly one EVENT_ROLE qualifier and no other qualifier. It must be referenced by at least one valid assertion so the role is an attributed structural fact. The assertion retains source, source instance, scope, availability, origin, conflict, and any permitted lineage. The relation type itself has no origin and cannot authenticate role.

PROPOSAL and EXECUTION are neutral lifecycle names: one identifies a declaration event and the other identifies an occurrence claimed as execution. They do not describe policy, outcome, authorization, quality, or ethics. UNKNOWN is the only additional required value. OBSERVATION is not added: V1.1 already represents observations through OBSERVED assertions and OBSERVED_BY, and adding the role would duplicate rather than enable execution-to-proposal endpoint validation.

## Claims, conflicts, and identity

Role is a source-attributed claim, not an intrinsic global fact. A source can claim an EVENT has EXECUTION role, and another source can claim PROPOSAL role. Both relations/assertions remain preserved as conflict; no source count, recency, ordering, or trust policy selects a winner.

Within one coherent producer record, PROPOSAL and EXECUTION asserted for the same scoped event are CONFLICT, not an identity collapse. They are not structurally malformed merely because different sources can disagree. The producer contract for Task 8/10 must keep proposal_id and execution_id distinct. UNKNOWN is epistemic and does not conflict with an explicit supported role; it supplies no endpoint support.

The role is attached to a resident EVENT in its existing scope. Same event IDs in different packets/scopes remain separate scoped evidence; current V1.1 packet indexing does not support same raw entity ID twice in one packet, and Task 13 does not revise that general identity rule. Cross-scope references may remain visible only when both resident endpoints and their role claims are supplied; no scope equivalence, authority, or trust inference follows.

## Future REFERENCES_PROPOSAL validation

A future V1.2 relation:

REFERENCES_PROPOSAL(execution: EVENT, proposal: EVENT)

is structurally supported only when:

1. the execution endpoint has at least one asserted HAS_EVENT_ROLE with EVENT_ROLE=EXECUTION;
2. the proposal endpoint has at least one asserted HAS_EVENT_ROLE with EVENT_ROLE=PROPOSAL;
3. both role relations and the reference relation are resident, typed, vocabulary-valid, and assertion-attributed;
4. no required role support is merely opaque text, ID syntax, metadata, timestamp, actor, target, gate result, or relation position.

The relation remains structurally valid in the presence of separately retained conflicting role claims; consumers may later apply their own conflict policy. A missing or only UNKNOWN role produces deterministic QUARANTINE for REFERENCES_PROPOSAL due to missing role support. A role relation whose event is nonresident is QUARANTINED as dangling. Wrong EVENT type, wrong role label, missing/extra qualifier, or wrong endpoint role is rejected or quarantined according to the normal finite-vocabulary and endpoint rules.

Relation direction matters: EXECUTION source to PROPOSAL destination has support. Reversed PROPOSAL to EXECUTION, EXECUTION to EXECUTION, PROPOSAL to PROPOSAL, and either UNKNOWN endpoint lack required support and are quarantined. This is role validation, not inferred chronology.

## Independence boundaries

Role does not imply time, actor, target, gate, authorization, outcome, or verification. A proposal can be BLOCKed; an execution can reference it through independently supplied role and reference claims, with no structural conclusion. Role claims remain stable even when timestamps conflict. A role supports neither a target nor an actor claim. Verification can verify one role assertion, one event-existence assertion, or one reference assertion only; it does not verify all event facts.

Lineage is not role. Producer identity is not role. A derived role assertion must meet ordinary lineage rules; an echo remains an echo and does not become independent support. In a swarm, A can assert P is PROPOSAL, B can assert E is EXECUTION, C can assert the reference, D can verify only E existence, and another source can issue a conflicting role assertion. All remain separate attributed facts.

## Adversarial matrix

| Case | Deterministic result |
| --- | --- |
| Valid PROPOSAL or EXECUTION role | STRUCTURAL when exact qualifier, resident EVENT, and attributed assertion exist. |
| Event with no role or UNKNOWN only | Role unavailable; cannot support reference endpoint. |
| Same event asserted as both roles | Retained CONFLICT; no global winner. |
| Same ID in different scope/packet | Separate scoped evidence; no global role merge. |
| Forged/cross-agent role | Attributed claim only. |
| Exact duplicate role assertion | Exact replay. |
| Divergent same relation ID | REJECTED collision. |
| Role before event or after consumer boundary | Dangling role QUARANTINED; late valid role not eligible for earlier consumer boundary. |
| Role in ID/text/gate/timestamp only | No structural role support. |
| Malformed or future role vocabulary | QUARANTINED. |
| Valid EXECUTION → PROPOSAL | STRUCTURAL if both asserted supports exist. |
| Reversed, same-role, or UNKNOWN endpoint pair | QUARANTINED for missing required role support. |

## V1.2 architecture and serialization

A future successor should use strategy B: a separate ethos_structural_evidence_v12.py and test_ethos_structural_evidence_v12.py, leaving frozen V1.1 files byte-for-byte unchanged.

V1.2 adds EVENT_ROLE qualifier vocabulary, HAS_EVENT_ROLE, REFERENCES_PROPOSAL, and cross-relation role-support validation. It does not add a new Entity field or record type. Canonical dataclass shape stays unchanged because Relation already contains relation_type, endpoints, qualifiers, and vocabulary_version. V1.2 packets identify successor vocabulary through vocabulary_version. V1.1 canonical bytes remain reproducible and do not acquire either vocabulary item.

## Minimality and decision

This introduces only the attributed role fact needed to distinguish proposal EVENT from execution EVENT for endpoint validation. It adds no observation lifecycle role, producer, runtime, policy, regulator consumer, execution result, authority, or ethical semantics.

EVENT ROLE CONTRACT REVISION READY FOR V1.2 AUTHORIZATION


# ETHOS++ — Task 11

## Execution → Proposal Structural Relation Gap Review

Status: structural contract review only. No V1.1, producer, or production change is authorized.

## Conclusion

No existing V1.1 representation expresses the fact exactly:

Execution E explicitly references Proposal P as its originating or associated proposal.

A minimal neutral relation extension is justified. The proposed relation is REFERENCES_PROPOSAL with endpoint roles execution and proposal. It states only a source-attributed structural reference between two EVENT entities.

It does not state causation, approval, authorization, faithful adherence, shared actor, shared target, completion, outcome, policy, responsibility, or ethical equivalence.

## Existing vocabulary audit

| Existing mechanism | Actual validated semantics | Result for E → P reference |
| --- | --- | --- |
| PARTICIPATES_IN | PARTICIPANT to EVENT | SEMANTICALLY DISTORT: participation is not reference. |
| TARGETS | EVENT to typed non-event target | NOT REPRESENT: proposal EVENT cannot be target endpoint. |
| REQUESTED_BY / REQUESTED_OF | PARTICIPANT requester to EVENT/TASK requested | SEMANTICALLY DISTORT and endpoint-invalid for EVENT to EVENT reference. |
| HAS_STATE / HAS_OUTCOME | One subject with supported qualifier | NOT REPRESENT: no second endpoint or reference. |
| OBSERVED_BY | PARTICIPANT/ENVIRONMENT observer to entity | SEMANTICALLY DISTORT: observing is not reference. |
| BEFORE / AFTER | EVENT to EVENT temporal ordering | SEMANTICALLY DISTORT: order is not association. |
| Assertion relation_ids | Assertion references relation records | NOT REPRESENT: not a relation between lifecycle entities. |
| Derived lineage | DERIVED assertion and parent assertions | SEMANTICALLY DISTORT: implies derivation. |
| Verification | Verification of one assertion | SEMANTICALLY DISTORT: implies a verification act. |
| Scope, source, shared actor/target, task text, ID convention | Provenance/co-occurrence only | NOT REPRESENT: none establishes explicit linkage. |

The frozen validator requires a relation type from its finite vocabulary, exact endpoint roles/cardinality, and endpoint entity types. Unsupported relation vocabulary is quarantined; event-as-target for TARGETS is rejected; dangling endpoints are quarantined. Therefore technical connectivity is not semantic representation.

## Minimum relation

Proposed vocabulary entry:

REFERENCES_PROPOSAL:
- execution: EVENT
- proposal: EVENT

Semantics: the assertion source explicitly states that the execution event references the proposal event. The relation is referential only. Relation type never supplies assertion origin; origin remains DECLARED, OBSERVED, or DERIVED on the assertion that references it, and fact-specific verification remains separate.

Proposal as EVENT is appropriate because Task 8/9 maps proposal_id to the event representing the declared proposal. Execution is separately an EVENT. Neither ID convention nor event type distinguishes occurrence; producer provenance and assertions do.

V1.1 has no EVENT subtype. EVENT endpoint typing rejects a TASK or PARTICIPANT in either role, but cannot by itself distinguish a proposal EVENT from an observation EVENT. A future producer profile must require the proposal endpoint to be an explicitly supplied Task 8/9 proposal record in the same input/evidence set. An observation EVENT presented as that endpoint is structurally EVENT-to-EVENT but unsupported by that producer profile and must be quarantined there. Adding an event subtype solely for this check is not justified by this narrow review.

## Cardinality and absence

A proposal has zero or many execution references. An execution has zero or one proposal reference in a single coherent producer record. Zero is valid because a source may not know the proposal. The relation vocabulary itself should not silently discard distinct attributed claims: different assertions may preserve conflicting execution-to-proposal references. A producer claiming two different proposals for one execution must either emit separately attributed conflicting claims or reject its own single-record shape; no majority or inferred primary proposal exists.

A missing reference is UNKNOWN or unavailable, not invalid execution. A referenced proposal absent from the packet is a dangling endpoint under current V1.1 behavior and therefore QUARANTINED, not invented. The minimal relation is packet-resident only. Cross-packet/external references need a later explicit external-reference design; opaque metadata may retain provenance but is non-consumable.

## Scope, target, actor, gate, and time

The current validator verifies endpoint presence and types but does not impose equal scopes. Do not add same-session, same-run, source-instance, or same-agent requirements to the relation: delegated and swarm executions can legitimately cross those boundaries. Both entity scopes remain visible; a future consumer supplies any cross-scope admissibility policy.

Proposal/execution target mismatch and actor mismatch are retained as independent relations. REFERENCES_PROPOSAL neither reconciles nor evaluates them. A proposal with ALLOW, BLOCK, or no gate record can be referenced by an independently supplied execution claim. The relation carries no gate result.

The relation contains no time. Conflicting timestamps or BEFORE/AFTER claims remain separate temporal evidence. They do not invalidate a structurally valid reference merely because they appear surprising. Malformed endpoint roles, cardinality, or types fail deterministically through ordinary relation validation.

## Replay, origin, authentication, and swarm

Exact duplicate relations are structural replays under existing canonical duplicate handling. A relation ID with different content is an ID collision and rejected. One proposal referenced by many execution events is valid. A forged reference is preserved only as a source assertion, not authentication. Echoed/derived reports must use explicit lineage; copied reports do not acquire independent status.

For N agents: A may propose P, B may execute E, C may assert the relation, and D may verify a separate assertion. The relation retains each provenance boundary and asserts no delegation, authority, responsibility, or blame.

## Adversarial review

| Case | Classification |
| --- | --- |
| Valid E → P | STRUCTURAL when both resident EVENT endpoints and a valid assertion are present. |
| Missing/unknown P | No relation is valid; retain UNKNOWN or unavailable separately. |
| Nonresident P | QUARANTINED dangling endpoint; no placeholder entity. |
| Cross-session or cross-agent P | Structurally allowed with visible scopes; no trust inference. |
| Target or actor mismatch | STRUCTURAL relation survives; facts remain separate. |
| BLOCK P with E | STRUCTURAL if independently asserted; no gate conclusion. |
| One P / many E | STRUCTURAL. |
| One E / conflicting P references | Preserve separately attributed conflict; producer cannot select one. |
| Exact duplicate relation | Exact replay. |
| Divergent relation under same relation ID | REJECTED collision. |
| Forged or echoed relation | Retained as attributed assertion/lineage, not authenticated. |
| Temporal contradiction | Retain explicit relation and conflicting temporal evidence. |
| Malformed endpoint or role | REJECTED. |
| Relation to TASK as proposal | REJECTED by endpoint contract. |
| Observation EVENT presented as proposal | EVENT typing alone accepts it; future producer profile QUARANTINES it unless it is an explicitly supplied proposal record. |
| Relation available after consumer boundary | Not eligible for that consumer; relation remains structurally valid. |

## V1.1 implications

V1.1 is frozen. If authorized, this must be a versioned successor, not a mutation of the frozen V1.1 contract. Required work would be:

1. define successor vocabulary/version policy;
2. add REFERENCES_PROPOSAL to the finite relation schema with exact EVENT endpoints;
3. preserve existing validation, duplicate/collision, canonicalization, scope, origin, temporal-availability, and verification rules;
4. add positive, endpoint, dangling-reference, replay/collision, conflict, cross-scope, time-boundary, and semantic-isolation tests;
5. authorize a test-only producer separately.

The canonical object shape need not change because Relation already serializes relation_type, endpoints, and vocabulary_version. Successor packets must identify the new vocabulary version, so their canonical bytes differ. Frozen V1.1 packet bytes and hashes must remain unchanged; compatibility for old records requires an explicit multi-version policy.

## Neutrality

REFERENCES_PROPOSAL is useful to runtime tracing, swarm coordination, auditing, Sloth, Wrath, and future consumers as a neutral graph edge. It adds no consumer routing and contains no regulator or policy terminology.

## Decision

MINIMAL NEUTRAL EXECUTION-PROPOSAL RELATION EXTENSION JUSTIFIED

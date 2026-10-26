# ETHOS++ — Task 14

## Structural Evidence V1.2 Revised Authorization

Status: authorization review only. Task 14 creates no implementation.

## Decision

STRUCTURAL EVIDENCE V1.2 MINIMAL EXTENSION AUTHORIZED.

Task 13 resolves the Task 12 blocker. A V1.2 validator can now mechanically require explicit, assertion-attributed event-role support for both endpoints of REFERENCES_PROPOSAL. It performs no ID, text, timestamp, actor, target, source-name, relation-position, or gate-result inference.

## Frozen V1.1 and isolation

V1.1 implementation hash: 6507e4ec3e0ed2898535e52dd15af1dffe8c7fa0a9bd8c33634f3868e8cbb2b3.

V1.1 test hash: 5ea43255794f9633214d8c6e91d1ee9b076bb9e3c634f2de0a76c4c857e1f8a9.

V1.1 remains byte-for-byte frozen. It continues to require STRUCTURAL_EVIDENCE_V1_1 and quarantines REFERENCES_PROPOSAL, HAS_EVENT_ROLE, and EVENT_ROLE as unsupported vocabulary. No V1.1 packet inherits V1.2 relations or qualifiers.

Task 15 may create only ethos_structural_evidence_v12.py and test_ethos_structural_evidence_v12.py. No existing file may be modified.

## Authorized V1.2 additions

1. V1.2 vocabulary marker STRUCTURAL_EVIDENCE_V1_2.
2. EVENT_ROLE finite qualifier vocabulary: PROPOSAL, EXECUTION, UNKNOWN.
3. HAS_EVENT_ROLE with exactly one event endpoint of type EVENT, exactly one EVENT_ROLE qualifier, and no additional qualifier.
4. REFERENCES_PROPOSAL with exactly two endpoints: execution EVENT and proposal EVENT.
5. Deterministic assertion-attribution and role-support validation for the two new relations.

No other entity type, qualifier, relation, record, runtime, producer, or consumer capability is authorized.

## Role and reference contract

PROPOSAL means only an attributed assertion identifies an event as having proposal lifecycle role. EXECUTION means only an attributed assertion identifies an event as having execution lifecycle role. UNKNOWN explicitly supplies no known role. All are claims with normal source, source instance, scope, availability, origin, conflict, lineage, and fact-specific verification boundaries.

HAS_EVENT_ROLE must be referenced by at least one structurally valid assertion. A standalone role relation is quarantined as unattributed. Role is never inferred from event identity, text, source name, actor, target, timestamp, relation position, or gate result.

REFERENCES_PROPOSAL means only: an attributed assertion claims execution-role event E references proposal-role event P. It implies no causation, authorization, approval, gate result, adherence, success, actor/target equivalence, responsibility, delegation, compliance, policy result, or ethical meaning. The reference relation itself must be assertion-attributed.

## Deterministic endpoint support

A REFERENCES_PROPOSAL relation is structurally supported only if the packet includes:

- a valid, assertion-attributed HAS_EVENT_ROLE E = EXECUTION;
- a valid, assertion-attributed HAS_EVENT_ROLE P = PROPOSAL; and
- a valid, assertion-attributed reference relation E → P.

Missing role, UNKNOWN-only role, dangling role event, missing resident proposal, wrong endpoint type, malformed qualifier, unsupported role, or reversed/same-role direction fails deterministically. Missing support is quarantined; endpoint/cardinality violations reject; unsupported finite vocabulary quarantines. No placeholder event or role evidence is created.

Conflicting claims are deterministic: retain all attributed role assertions. If E has both EXECUTION and PROPOSAL claims, the conflict remains; it may supply explicit EXECUTION support to a reference but does not establish a global role truth. This is sufficient for the narrow source-attributed reference fact and insufficient for any consumer to infer trust, responsibility, or exclusive lifecycle identity. Consumer conflict policy is outside V1.2.

Proposal_id and execution_id remain distinct lifecycle identities. Same raw ID has no role meaning. Roles attach to resident scoped events. Cross-session, cross-run, and cross-agent references are structurally possible when endpoint events and supporting role claims are present, but no scope equivalence, authority, or legitimacy inference is made.

## Time, provenance, verification, and observation

Role and reference assertions retain normal availability/provenance/lineage. They can be structurally valid after a consumer boundary yet are not eligible for an earlier evaluation; existing temporal eligibility rules control consumer-time selection. REFERENCES_PROPOSAL establishes no BEFORE, AFTER, or causality.

Verification can independently verify event existence, a role assertion, or a reference assertion. Verifying one fact verifies no other event fact. Existing OBSERVED assertion and OBSERVED_BY structures continue to represent observation; OBSERVATION role is neither needed nor authorized.

## Successor architecture and serialization

Use separate V1.2 validation code. It may import immutable V1.1 data carriers and canonical serialization helpers only if it never mutates V1.1 constants, schemas, validators, defaults, or behavior. V1.2 owns its vocabulary tables, successor validator, and explicit V1.2 relation construction/validation. The inherited Relation default is V1.1, so V1.2 tests and producers must explicitly supply STRUCTURAL_EVIDENCE_V1_2; no implicit default is permitted.

Canonical dataclass shape remains unchanged: the new role is expressed through existing Relation endpoints and Qualifier fields. V1.2 bytes identify their vocabulary through Relation.vocabulary_version. Unknown/future versions quarantine. V1.1 canonical bytes remain reproducible from the frozen module.

## Required Task 15 tests

Task 15 must cover all 33 required cases: valid and UNKNOWN roles; malformed/unsupported roles; missing/dangling events; conflicts; valid/reversed/same-role/unknown endpoint references; missing source/destination role; cross-scope, actor, target, and BLOCK independence; duplicate/collision, conflicting references, replay/lineage, temporal contradiction, future-evidence boundary, forged claims; V1.1 rejection/quarantine; V1.2 acceptance; future version rejection; canonical round-trip/determinism; and frozen V1.1 hashes.

A semantic-isolation test must ensure the successor contains no shared interpretation of aggression, retaliation, coercion, harm, responsibility, authorization, approval, compliance, disobedience, Wrath, Sloth, ethics, violation, score, or policy.

## Deferred

Execution producer/runtime, ActionProposal and CLI changes, observations, outcomes, measurements, authorization, gate/controller/EvidenceView integration, Wrath integration, and all regulator consumers remain deferred.

## Decision

STRUCTURAL EVIDENCE V1.2 MINIMAL EXTENSION AUTHORIZED


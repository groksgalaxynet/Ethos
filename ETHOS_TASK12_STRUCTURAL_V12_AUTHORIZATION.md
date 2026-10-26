# ETHOS++ — Task 12

## Structural Evidence V1.2 Minimal Extension Authorization

Status: authorization review only. No implementation is authorized.

## Decision

STRUCTURAL EVIDENCE V1.2 AUTHORIZATION BLOCKED — CONTRACT REVISION REQUIRED.

Task 11 correctly established that no existing V1.1 relation represents an explicit execution-to-proposal reference. REFERENCES_PROPOSAL is neutral in intent. However, the proposed relation-only V1.2 is not authorized because its endpoint contract cannot be mechanically enforced with V1.1 entity types alone.

## Frozen V1.1

The frozen implementation hash is 6507e4ec3e0ed2898535e52dd15af1dffe8c7fa0a9bd8c33634f3868e8cbb2b3. The frozen test hash is 5ea43255794f9633214d8c6e91d1ee9b076bb9e3c634f2de0a76c4c857e1f8a9.

V1.1 must remain byte-for-byte unchanged. It must continue to quarantine unsupported relation vocabulary, including REFERENCES_PROPOSAL, under its existing STRUCTURAL_EVIDENCE_V1_1 relation vocabulary. Existing V1.1 canonical bytes remain reproducible by retaining the existing module and tests unchanged.

## Proposed relation and required semantics

The candidate name remains REFERENCES_PROPOSAL.

Its intended meaning is only: the assertion source claims execution EVENT E references proposal EVENT P. It must not imply causation, authorization, approval, gate ALLOW, adherence, success, shared actor, shared target, responsibility, delegation, ethical acceptability, or policy result.

The intended relation roles are execution and proposal, with EVENT endpoints. Proposal cardinality is zero-or-many executions. A coherent producer record contains zero-or-one proposal reference for an execution; separately attributed conflicting claims remain separate and unresolved. Missing linkage is UNKNOWN or unavailable. A dangling resident-packet reference follows existing quarantine behavior and never creates a placeholder.

Cross-scope references remain visible and neutral; no same-agent, same-session, identity-equivalence, trust, or authority rule follows. Target, actor, gate, and temporal mismatches remain retained independent evidence. Relation origin is supplied by its assertion envelope. Verification remains fact-specific.

## Authorization blocker: EVENT role ambiguity

V1.1 has one EVENT entity type. Relation validation verifies only relation type, endpoint role names, endpoint cardinality, endpoint presence, and entity types. It cannot determine whether an EVENT assigned role proposal is actually:

- a Task 8/9 declared proposal event;
- an execution event;
- an observation event; or
- another event.

Role labels are producer-supplied strings, not entity-kind proof. IDs, text, scope, source, opaque metadata, shared target, and ordering cannot safely fill this gap. A relation-only V1.2 would mechanically accept execution EVENT → observation EVENT as REFERENCES_PROPOSAL. That violates the required endpoint-enforcement criterion.

A producer profile could quarantine such input using external knowledge, but that is not Structural Evidence endpoint enforcement and cannot satisfy this authorization. The present task allows only relation and version changes, so it cannot add the missing neutral event-role capability.

## Required contract revision before reconsideration

A later design task must choose and adversarially review one minimal structural method to establish proposal-event role, such as a finite neutral event-kind field or a separately typed proposal-event representation. It must define:

1. exact vocabulary and UNKNOWN behavior;
2. provenance and scope rules;
3. canonical/version compatibility;
4. whether an observation/event distinction is enforceable;
5. V1.1 preservation and multi-version reading;
6. failure disposition for absent, malformed, forged, and conflicting role evidence.

Only after that review can REFERENCES_PROPOSAL use mechanically distinguishable endpoints. No identity naming convention, opaque metadata convention, or relation role label is an acceptable substitute.

## Version and serialization strategy

If a revised contract is later authorized, strategy B is safest: create a separate V1.2 module and V1.2 tests while preserving the V1.1 module and tests byte-for-byte. V1.2 packets must carry an explicit successor vocabulary version in Relation.vocabulary_version. Canonical relation object shape can remain unchanged, but successor bytes must differ through vocabulary version and any separately authorized role representation. Old packets never silently inherit V1.2 vocabulary.

Current V1.1 has one CONTRACT_VERSION and requires relation vocabulary_version to equal it. Any compatibility bridge must be separately specified; changing that behavior in the frozen module is out of scope.

## Required future tests after revision

A future authorization must require V1.1 preservation/byte fixtures; V1.1 rejection of REFERENCES_PROPOSAL; V1.2 valid relation; both wrong endpoint types; proposal-role versus observation-event rejection; dangling proposal; replay/collision; conflicting references; cross-scope relation; actor/target/gate mismatch; temporal conflict; assertion origin; verification; future/unknown version; availability boundary; forged source; and semantic-isolation checks.

## Neutrality and deferrals

The candidate relation itself adds no regulator, policy, or ethical interpretation. The authorization block is structural, not semantic. Execution producers, runtime execution, observations, outcomes, measurements, authority, gate integration, Wrath integration, and all regulator consumers remain explicitly deferred.

## Future file boundary

No implementation is authorized now. After a contract-revision authorization, the smallest anticipated new files are:

- ethos_structural_evidence_v12.py
- test_ethos_structural_evidence_v12.py

The frozen V1.1 implementation and its test file must not be modified. A future producer remains a separate task.

## Decision

STRUCTURAL EVIDENCE V1.2 AUTHORIZATION BLOCKED — CONTRACT REVISION REQUIRED


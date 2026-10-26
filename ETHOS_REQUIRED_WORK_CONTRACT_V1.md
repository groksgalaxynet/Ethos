# ETHOS++ Required Work Contract V1

## Purpose

`RequiredWorkAssignment` is a research-only, neutral, source-attributed claim: issuer I assigned work W within objective O to actor A in scope S with requirement R. It establishes factual obligation evidence only. It never asserts avoidance, intent, fault, Sloth, policy violation, or a gate outcome.

The contract reuses the research-only factual-context `Source` and `VerificationState` vocabularies. That existing model represents responsibility, task requirement, authorization, and completion, but lacks assignment identity, issuer/assignee binding, scope binding, authority reference, and lifecycle claims. This contract adds only those facts.

## Minimum schema

Required fields are assignment ID, objective ID, work ID, assigned actor ID, issuer ID, requirement, assignment timestamp, and attribution. Attribution contains source, source instance ID, scope ID, availability time, verification state, and evidence reference. An authority ID is optional because it may be unavailable, but no downstream consumer may treat it as confirmed by default.

Requirement is exactly `REQUIRED`, `OPTIONAL`, or `UNKNOWN`. UNKNOWN is valid epistemic content and yields `UNKNOWN_REQUIREMENT`; malformed data yields `MALFORMED` and is distinct from UNKNOWN.

## Authority and provenance

Authority is fact-specific and external to the assignment payload. `AuthorityClaim` names authority ID, issuer ID, fact class `ASSIGN_REQUIRED_WORK`, disposition (`CONFIRMED`, `DENIED`, or `UNKNOWN`), and independent attribution. The prototype does not decide which user, controller, scheduler, parent agent, workflow, or runtime is authoritative. An assignment issuer cannot self-grant authority through metadata.

Matching `CONFIRMED` authority and correct actor/scope produce `REQUIRED_ACTIVE` or `OPTIONAL_ACTIVE`. Missing, mismatched, denied, or unknown authority produces `UNRESOLVED_AUTHORITY` or `UNAUTHORIZED_ASSIGNMENT`.

## Lifecycle

Lifecycle is an immutable `AssignmentLifecycleClaim`, separate from the assignment. States are `ACTIVE`, `COMPLETED`, `CANCELLED`, `SUPERSEDED`, `BLOCKED`, `DELEGATED`, and `EXPIRED`.

Completed, cancelled, superseded, and expired work is not current required work. Blocked work yields `BLOCKED`, not non-completion. Delegation requires a delegate actor ID and yields `DELEGATED_AWAY` or `DELEGATED_TO_SELF`; it never establishes avoidance. Multiple lifecycle states yield `LIFECYCLE_CONFLICT`, never silent resolution.

## Action-decision linkage and blockers

`ActionDecisionRecord` candidate `action_id` maps explicitly to assignment `work_id`; objective IDs must match. A later consumer must require the same actor, scope, and `REQUIRED_ACTIVE` evidence before considering an action required. This contract adds no Sloth classifier.

The action-decision research record already represents candidate availability and factual `VALID_BLOCKER` or `PREREQUISITE` claims. This contract adds assignment lifecycle `BLOCKED`. A blocked/unavailable action, missing prerequisite, insufficient permission, or insufficient resources remains factual context, never a Sloth excuse or judgment here.

## Non-goals and coverage

No production import, ProposalGate connection, regulator promotion, execution claim, completion inference, hidden reasoning, priority guess, benefit score, or ethical judgment is introduced. Structural Evidence V1.1/V1.2 remains unchanged. V1.2 may later link events structurally but does not establish authority or obligation.

Fixtures cover authorized user/controller required work, optional/suggestion/unauthorized idea, completed/cancelled/superseded/delegated/blocked/expired states, unknown authority, malformed assignment, wrong actor, scope mismatch, and lifecycle conflict. Every output is factual evidence state only.

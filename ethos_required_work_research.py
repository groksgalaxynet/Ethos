"""Research-only, neutral required-work assignment evidence contract."""
from __future__ import annotations

from dataclasses import dataclass

from factual_context_research import Source, VerificationState

REQUIRED = "REQUIRED"
OPTIONAL = "OPTIONAL"
UNKNOWN = "UNKNOWN"
LIFECYCLE_VALUES = frozenset({"ACTIVE", "COMPLETED", "CANCELLED", "SUPERSEDED", "BLOCKED", "DELEGATED", "EXPIRED"})


@dataclass(frozen=True)
class Attribution:
    source: Source
    source_instance_id: str
    scope_id: str
    available_at: str
    verification: VerificationState
    evidence_reference: str | None


@dataclass(frozen=True)
class AuthorityClaim:
    authority_id: str
    issuer_id: str
    fact_class: str
    disposition: str  # CONFIRMED, DENIED, UNKNOWN; supplied by a separate resolver
    attribution: Attribution


@dataclass(frozen=True)
class RequiredWorkAssignment:
    assignment_id: str
    objective_id: str
    work_id: str
    assigned_actor_id: str
    issuer_id: str
    requirement: str
    assignment_at: str
    attribution: Attribution
    authority_id: str | None = None


@dataclass(frozen=True)
class AssignmentLifecycleClaim:
    claim_id: str
    assignment_id: str
    state: str
    attribution: Attribution
    delegate_actor_id: str | None = None


def validate_assignment(value: RequiredWorkAssignment) -> tuple[str, ...]:
    issues = []
    if not all((value.assignment_id, value.objective_id, value.work_id, value.assigned_actor_id, value.issuer_id, value.assignment_at)):
        issues.append("MISSING_ASSIGNMENT_IDENTITY")
    if value.requirement not in {REQUIRED, OPTIONAL, UNKNOWN}:
        issues.append("INVALID_REQUIREMENT")
    issues.extend(_attribution_issues(value.attribution))
    return tuple(sorted(set(issues)))


def validate_lifecycle(value: AssignmentLifecycleClaim) -> tuple[str, ...]:
    issues = []
    if not value.claim_id or not value.assignment_id or value.state not in LIFECYCLE_VALUES:
        issues.append("INVALID_LIFECYCLE")
    if value.state != "DELEGATED" and value.delegate_actor_id is not None:
        issues.append("UNEXPECTED_DELEGATE")
    if value.state == "DELEGATED" and not value.delegate_actor_id:
        issues.append("MISSING_DELEGATE")
    issues.extend(_attribution_issues(value.attribution))
    return tuple(sorted(set(issues)))


def assignment_state(
    assignment: RequiredWorkAssignment,
    authority: AuthorityClaim | None,
    lifecycle: tuple[AssignmentLifecycleClaim, ...],
    actor_id: str,
    scope_id: str,
) -> str:
    """Return only factual obligation evidence; never a Sloth conclusion."""
    if validate_assignment(assignment) or any(validate_lifecycle(item) for item in lifecycle):
        return "MALFORMED"
    if assignment.assigned_actor_id != actor_id:
        return "OTHER_ACTOR"
    if assignment.attribution.scope_id != scope_id:
        return "SCOPE_MISMATCH"
    if assignment.requirement == UNKNOWN:
        return "UNKNOWN_REQUIREMENT"
    if authority is None or authority.authority_id != assignment.authority_id or authority.fact_class != "ASSIGN_REQUIRED_WORK":
        return "UNRESOLVED_AUTHORITY"
    if authority.disposition == "DENIED":
        return "UNAUTHORIZED_ASSIGNMENT"
    if authority.disposition != "CONFIRMED":
        return "UNRESOLVED_AUTHORITY"
    states = {item.state for item in lifecycle}
    if len(states) > 1:
        return "LIFECYCLE_CONFLICT"
    state = next(iter(states), "ACTIVE")
    if state == "COMPLETED":
        return "COMPLETED"
    if state == "CANCELLED":
        return "CANCELLED"
    if state == "SUPERSEDED":
        return "SUPERSEDED"
    if state == "EXPIRED":
        return "EXPIRED"
    if state == "BLOCKED":
        return "BLOCKED"
    if state == "DELEGATED":
        delegate = lifecycle[0].delegate_actor_id
        return "DELEGATED_AWAY" if delegate != actor_id else "DELEGATED_TO_SELF"
    return "REQUIRED_ACTIVE" if assignment.requirement == REQUIRED else "OPTIONAL_ACTIVE"


def _attribution_issues(value: Attribution) -> list[str]:
    if not all((value.source_instance_id, value.scope_id, value.available_at)):
        return ["INVALID_ATTRIBUTION"]
    if value.source is Source.UNKNOWN_SOURCE or value.verification is VerificationState.UNKNOWN:
        return []  # epistemically valid, but downstream state remains unresolved
    return []

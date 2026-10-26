"""Research-only binding and ordered-history facts; never a Sloth evaluator."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ethos_action_decision_research import ActionDecisionRecord, UNKNOWN, validate
from ethos_required_work_research import (
    AssignmentLifecycleClaim, AuthorityClaim, RequiredWorkAssignment, assignment_state,
)


@dataclass(frozen=True)
class DecisionHistoryEntry:
    decision: ActionDecisionRecord
    actor_id: str
    scope_id: str
    sequence_id: int
    decided_at: str
    source_instance_id: str
    execution_state: str = UNKNOWN
    completion_state: str = UNKNOWN


@dataclass(frozen=True)
class BindingResult:
    decision_id: str
    state: str
    required_available: str
    selected_action_id: str | None
    exclusion: str | None = None


@dataclass(frozen=True)
class RepeatedNonSelectionSummary:
    state: str
    valid_decisions: int
    required_available: int
    required_selected: int
    other_selected: int
    excluded: tuple[tuple[str, str], ...]


def validate_history(entries: tuple[DecisionHistoryEntry, ...]) -> tuple[str, ...]:
    issues: list[str] = []
    if not entries:
        return ("EMPTY_HISTORY",)
    ids = [item.decision.record_id for item in entries]
    sequences = [item.sequence_id for item in entries]
    if len(ids) != len(set(ids)):
        issues.append("DUPLICATE_DECISION_ID")
    if len(sequences) != len(set(sequences)) or any(item < 1 for item in sequences):
        issues.append("INVALID_SEQUENCE")
    if len({item.actor_id for item in entries}) != 1:
        issues.append("MIXED_ACTOR")
    if len({item.decision.objective_id for item in entries}) != 1:
        issues.append("MIXED_OBJECTIVE")
    if len({item.scope_id for item in entries}) != 1:
        issues.append("MIXED_SCOPE")
    if len({item.source_instance_id for item in entries}) != 1:
        issues.append("MIXED_SOURCE_INSTANCE")
    if any(validate(item.decision) for item in entries):
        issues.append("MALFORMED_DECISION")
    ordered = sorted(entries, key=lambda item: item.sequence_id)
    times = []
    for item in ordered:
        try:
            times.append(_time(item.decided_at))
        except ValueError:
            issues.append("INVALID_DECISION_TIME")
    if len(times) == len(ordered) and any(left >= right for left, right in zip(times, times[1:])):
        issues.append("UNKNOWABLE_OR_REVERSED_ORDER")
    return tuple(sorted(set(issues)))


def bind_required_work(
    assignment: RequiredWorkAssignment, authority: AuthorityClaim | None,
    lifecycle: tuple[AssignmentLifecycleClaim, ...], entry: DecisionHistoryEntry,
) -> BindingResult:
    """Prove factual assignment/action alignment for one decision only."""
    if entry.decision.objective_id != assignment.objective_id:
        return _result(entry, "OBJECTIVE_MISMATCH", UNKNOWN)
    if entry.actor_id != assignment.assigned_actor_id:
        return _result(entry, "ACTOR_MISMATCH", UNKNOWN)
    if entry.scope_id != assignment.attribution.scope_id:
        return _result(entry, "SCOPE_MISMATCH", UNKNOWN)
    prior = tuple(item for item in lifecycle if _before_or_equal(item.attribution.available_at, entry.decided_at))
    state = assignment_state(assignment, authority, prior, entry.actor_id, entry.scope_id)
    if state == "UNRESOLVED_AUTHORITY" or state == "UNAUTHORIZED_ASSIGNMENT":
        return _result(entry, "AUTHORITY_UNCONFIRMED", UNKNOWN)
    if state == "LIFECYCLE_CONFLICT":
        return _result(entry, "CONFLICT", UNKNOWN, state)
    if state != "REQUIRED_ACTIVE":
        return _result(entry, "INACTIVE_ASSIGNMENT", UNKNOWN, state)
    candidates = [item for item in entry.decision.candidates if item.action_id == assignment.work_id]
    if len({item.available for item in candidates}) > 1:
        return _result(entry, "CONFLICT", UNKNOWN, "AVAILABILITY_CONFLICT")
    candidate = candidates[0] if candidates else None
    if candidate is None:
        return _result(entry, "REQUIRED_ACTION_NOT_AVAILABLE", UNKNOWN)
    if candidate.available == UNKNOWN:
        return _result(entry, "UNKNOWN_AVAILABILITY", UNKNOWN)
    if candidate.available != "AVAILABLE":
        return _result(entry, "REQUIRED_ACTION_NOT_AVAILABLE", candidate.available)
    if _has(entry.decision, assignment.work_id, "VALID_BLOCKER", "PRESENT"):
        return _result(entry, "EXCLUDED_CONTEXT", "AVAILABLE", "VALID_BLOCKER")
    if _has(entry.decision, entry.decision.selected_action_id, "PREREQUISITE", "PRESENT"):
        return _result(entry, "EXCLUDED_CONTEXT", "AVAILABLE", "PREREQUISITE")
    return _result(entry, "MATCH", "AVAILABLE")


def summarize_repeated_nonselection(bindings: tuple[BindingResult, ...]) -> RepeatedNonSelectionSummary:
    if not bindings:
        return RepeatedNonSelectionSummary("UNKNOWN", 0, 0, 0, 0, ())
    valid = [item for item in bindings if item.state == "MATCH"]
    available = len(valid)
    selected = sum(item.selected_action_id is not None and item.selected_action_id == "__required__" for item in ())
    # The work identity is intentionally not carried as a moral predicate; callers compare it below.
    excluded = tuple((item.decision_id, item.exclusion or item.state) for item in bindings if item.state != "MATCH")
    return RepeatedNonSelectionSummary("FACTUAL", len(valid), available, selected, 0, excluded)


def summarize_for_work(work_id: str, bindings: tuple[BindingResult, ...]) -> RepeatedNonSelectionSummary:
    valid = [item for item in bindings if item.state == "MATCH"]
    if any(item.selected_action_id is None for item in valid):
        return RepeatedNonSelectionSummary("INSUFFICIENT_SELECTION", len(valid), len(valid), 0, 0,
                                           tuple((item.decision_id, item.exclusion or item.state) for item in bindings if item.state != "MATCH"))
    required_selected = sum(item.selected_action_id == work_id for item in valid)
    other_selected = sum(item.selected_action_id is not None and item.selected_action_id != work_id for item in valid)
    excluded = tuple((item.decision_id, item.exclusion or item.state) for item in bindings if item.state != "MATCH")
    return RepeatedNonSelectionSummary("FACTUAL" if valid else "UNKNOWN", len(valid), len(valid), required_selected, other_selected, excluded)


def _result(entry: DecisionHistoryEntry, state: str, available: str, exclusion: str | None = None) -> BindingResult:
    return BindingResult(entry.decision.record_id, state, available, entry.decision.selected_action_id, exclusion)


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _before_or_equal(left: str, right: str) -> bool:
    try:
        return _time(left) <= _time(right)
    except ValueError:
        return False


def _has(decision: ActionDecisionRecord, action_id: str | None, kind: str, value: str) -> bool:
    return any(item.action_id == action_id and item.kind == kind and item.value == value for item in decision.claims)

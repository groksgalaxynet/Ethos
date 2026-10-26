"""Research-only factual join for required-work decision context; never Sloth."""
from __future__ import annotations

from dataclasses import dataclass

from ethos_action_value_research import EXPECTED, MeasurementAuthorityClaim, MeasurementBasis, ValueClaim, compare_benefit, compare_effort
from ethos_decision_history_research import DecisionHistoryEntry, bind_required_work, validate_history
from ethos_required_work_research import AssignmentLifecycleClaim, AuthorityClaim, RequiredWorkAssignment


@dataclass(frozen=True)
class DecisionContextEvidence:
    decision_id: str
    state: str
    assignment_id: str
    required_action_id: str
    selected_action_id: str | None
    required_active: bool | None
    required_available: bool | None
    valid_blocker: bool | None
    prerequisite: bool | None
    required_selected: bool | None
    alternative_selected: bool | None
    required_higher_expected_benefit: bool | None
    selected_lower_expected_effort: bool | None
    benefit_comparison: str | None
    effort_comparison: str | None
    references: tuple[str, ...]


@dataclass(frozen=True)
class DecisionContextHistorySummary:
    state: str
    complete_contexts: int
    target_patterns: int
    required_selected: int
    alternative_selected: int
    excluded: int
    unknown: int
    conflicts: int
    not_comparable: int


def validate_context(
    assignment: RequiredWorkAssignment, assignment_authority: AuthorityClaim | None,
    lifecycle: tuple[AssignmentLifecycleClaim, ...], entry: DecisionHistoryEntry,
    benefit_a: tuple[ValueClaim, ...], benefit_b: tuple[ValueClaim, ...], benefit_basis: MeasurementBasis,
    effort_a: tuple[ValueClaim, ...], effort_b: tuple[ValueClaim, ...], effort_basis: MeasurementBasis,
    measurement_authorities: tuple[MeasurementAuthorityClaim, ...],
) -> DecisionContextEvidence:
    binding = bind_required_work(assignment, assignment_authority, lifecycle, entry)
    refs = (assignment.assignment_id, entry.decision.record_id, *(item.claim_id for item in (*benefit_a, *benefit_b, *effort_a, *effort_b)))
    if binding.state == "EXCLUDED_CONTEXT" or binding.state == "INACTIVE_ASSIGNMENT":
        return _context(entry, assignment, "EXCLUDED_CONTEXT", binding, None, None, refs)
    if binding.state == "CONFLICT":
        return _context(entry, assignment, "CONFLICT", binding, None, None, refs)
    if binding.state in {"UNKNOWN_AVAILABILITY", "AUTHORITY_UNCONFIRMED"}:
        return _context(entry, assignment, "UNKNOWN", binding, None, None, refs)
    if binding.state != "MATCH":
        return _context(entry, assignment, "INCOMPLETE_CONTEXT", binding, None, None, refs)
    if entry.decision.selected_action_id is None:
        return _context(entry, assignment, "UNKNOWN", binding, None, None, refs)
    if any(item.phase != EXPECTED for item in (*benefit_a, *benefit_b, *effort_a, *effort_b)):
        return _context(entry, assignment, "NOT_COMPARABLE", binding, None, None, refs)
    benefit = compare_benefit(benefit_a, benefit_b, benefit_basis, measurement_authorities, entry.decided_at)
    effort = compare_effort(effort_a, effort_b, effort_basis, measurement_authorities, entry.decided_at)
    if "CONFLICT" in {benefit, effort}:
        return _context(entry, assignment, "CONFLICT", binding, benefit, effort, refs)
    if "UNKNOWN" in {benefit, effort}:
        return _context(entry, assignment, "UNKNOWN", binding, benefit, effort, refs)
    if "NOT_COMPARABLE" in {benefit, effort}:
        return _context(entry, assignment, "NOT_COMPARABLE", binding, benefit, effort, refs)
    return _context(entry, assignment, "COMPLETE_CONTEXT", binding, benefit, effort, refs)


def summarize_contexts(entries: tuple[DecisionHistoryEntry, ...], contexts: tuple[DecisionContextEvidence, ...]) -> DecisionContextHistorySummary:
    if validate_history(entries) or len(entries) != len(contexts):
        return DecisionContextHistorySummary("UNKNOWN", 0, 0, 0, 0, 0, 0, 0, 0)
    complete = [item for item in contexts if item.state == "COMPLETE_CONTEXT"]
    return DecisionContextHistorySummary(
        "FACTUAL", len(complete),
        sum(item.required_higher_expected_benefit is True and item.selected_lower_expected_effort is True and item.alternative_selected is True for item in complete),
        sum(item.required_selected is True for item in complete), sum(item.alternative_selected is True for item in complete),
        sum(item.state == "EXCLUDED_CONTEXT" for item in contexts), sum(item.state == "UNKNOWN" for item in contexts),
        sum(item.state == "CONFLICT" for item in contexts), sum(item.state == "NOT_COMPARABLE" for item in contexts),
    )


def _context(entry, assignment, state, binding, benefit, effort, refs):
    selected = entry.decision.selected_action_id
    match = binding.state == "MATCH"
    active = match or binding.state in {"EXCLUDED_CONTEXT", "CONFLICT"}
    alternative = selected is not None and selected != assignment.work_id if match else None
    return DecisionContextEvidence(entry.decision.record_id, state, assignment.assignment_id, assignment.work_id, selected,
        active if match else None, binding.required_available == "AVAILABLE" if match else None,
        binding.exclusion == "VALID_BLOCKER", binding.exclusion == "PREREQUISITE",
        selected == assignment.work_id if match else None, alternative,
        benefit == "A_GREATER" if benefit else None, effort == "A_GREATER" if effort else None,
        benefit, effort, refs)

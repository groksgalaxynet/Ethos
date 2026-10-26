"""Isolated evidence-driven Sloth Research V1 evaluator; no production wiring."""
from __future__ import annotations

from dataclasses import dataclass

from ethos_decision_context_research import DecisionContextEvidence
from ethos_decision_history_research import DecisionHistoryEntry, validate_history


@dataclass(frozen=True)
class SlothEvaluationPolicy:
    minimum_repeated_avoidance_count: int = 2
    version: str = "SLOTH_RESEARCH_EVALUATOR_V1"

    def __post_init__(self):
        if self.minimum_repeated_avoidance_count < 1:
            raise ValueError("minimum_repeated_avoidance_count must be positive")


@dataclass(frozen=True)
class SlothEvaluationResult:
    state: str
    policy_version: str
    threshold: int
    qualifying_count: int
    qualifying_decision_ids: tuple[str, ...]
    required_selected_count: int
    excluded: tuple[tuple[str, str], ...]
    unknown: tuple[tuple[str, str], ...]
    conflicts: tuple[tuple[str, str], ...]
    not_comparable: tuple[tuple[str, str], ...]
    references: tuple[str, ...]
    reason_code: str


def evaluate_sloth_research(
    entries: tuple[DecisionHistoryEntry, ...], contexts: tuple[DecisionContextEvidence, ...],
    assignment_id: str, required_action_id: str, policy: SlothEvaluationPolicy = SlothEvaluationPolicy(),
) -> SlothEvaluationResult:
    """Evaluate only one coherent assignment/work history using upstream facts."""
    if validate_history(entries) or len(entries) != len(contexts) or len({item.decision_id for item in contexts}) != len(contexts):
        return _result("INSUFFICIENT_EVIDENCE", policy, (), 0, (), (), (), (), (), "INVALID_HISTORY")
    if any(item.assignment_id != assignment_id or item.required_action_id != required_action_id for item in contexts):
        return _result("INSUFFICIENT_EVIDENCE", policy, (), 0, (), (), (), (), (), "MIXED_OBLIGATION")
    by_id = {item.decision_id: item for item in contexts}
    if set(by_id) != {item.decision.record_id for item in entries}:
        return _result("INSUFFICIENT_EVIDENCE", policy, (), 0, (), (), (), (), (), "CONTEXT_HISTORY_MISMATCH")
    qualifying = tuple(item.decision_id for item in contexts if _qualifies(item))
    selected = sum(item.required_selected is True for item in contexts)
    excluded = tuple((item.decision_id, item.state) for item in contexts if item.state == "EXCLUDED_CONTEXT")
    unknown = tuple((item.decision_id, item.state) for item in contexts if item.state in {"UNKNOWN", "INCOMPLETE_CONTEXT"})
    conflicts = tuple((item.decision_id, item.state) for item in contexts if item.state == "CONFLICT")
    incomparable = tuple((item.decision_id, item.state) for item in contexts if item.state == "NOT_COMPARABLE")
    refs = tuple(item.decision_id for item in contexts)
    if len(qualifying) >= policy.minimum_repeated_avoidance_count:
        return _result("POSITIVE", policy, qualifying, selected, excluded, unknown, conflicts, incomparable, refs, "REPEATED_QUALIFYING_AVOIDANCE")
    if conflicts:
        return _result("CONFLICT", policy, qualifying, selected, excluded, unknown, conflicts, incomparable, refs, "CONFLICTING_EVIDENCE")
    if incomparable:
        return _result("NOT_COMPARABLE", policy, qualifying, selected, excluded, unknown, conflicts, incomparable, refs, "MEASUREMENTS_NOT_COMPARABLE")
    if unknown:
        return _result("INSUFFICIENT_EVIDENCE", policy, qualifying, selected, excluded, unknown, conflicts, incomparable, refs, "UNKNOWN_OR_INCOMPLETE_EVIDENCE")
    if excluded and not qualifying:
        return _result("EXCLUDED", policy, qualifying, selected, excluded, unknown, conflicts, incomparable, refs, "ALL_APPARENT_NONSELECTIONS_EXCLUDED")
    return _result("NEGATIVE", policy, qualifying, selected, excluded, unknown, conflicts, incomparable, refs, "THRESHOLD_NOT_MET")


def _qualifies(item: DecisionContextEvidence) -> bool:
    return item.state == "COMPLETE_CONTEXT" and item.required_active is True and item.required_available is True and item.valid_blocker is False and item.prerequisite is False and item.alternative_selected is True and item.required_higher_expected_benefit is True and item.selected_lower_expected_effort is True


def _result(state, policy, qualifying, selected, excluded, unknown, conflicts, incomparable, refs, code):
    return SlothEvaluationResult(state, policy.version, policy.minimum_repeated_avoidance_count, len(qualifying), tuple(qualifying), selected, tuple(excluded), tuple(unknown), tuple(conflicts), tuple(incomparable), tuple(refs), code)

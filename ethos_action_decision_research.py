"""Research-only neutral action-decision evidence model.

This module is intentionally outside the production proposal gate.  It records
source-attributed operational facts and provides conservative candidate-status
prototypes for contract fixtures only.  It has no policy, score, gate, history,
controller, executor, or production-regulator import.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

UNKNOWN = "UNKNOWN"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
NOT_INDICATED = "NOT_INDICATED"
CANDIDATE = "CANDIDATE"


@dataclass(frozen=True)
class SourceAttribution:
    source_id: str
    source_instance_id: str
    scope_id: str
    available_at: str


@dataclass(frozen=True)
class ActionCandidate:
    action_id: str
    objective_id: str
    benefit: float | None = None
    effort: float | None = None
    resource_cost: float | None = None
    required_status: str = UNKNOWN
    available: str = UNKNOWN


@dataclass(frozen=True)
class ContextClaim:
    claim_id: str
    action_id: str | None
    kind: str
    value: str
    source: SourceAttribution


@dataclass(frozen=True)
class ActionDecisionRecord:
    record_id: str
    objective_id: str
    candidates: tuple[ActionCandidate, ...]
    selected_action_id: str | None
    source: SourceAttribution
    claims: tuple[ContextClaim, ...] = ()
    execution_state: str = UNKNOWN
    outcome: str = UNKNOWN
    decision_count: int | None = None


def validate(record: ActionDecisionRecord) -> tuple[str, ...]:
    """Validate neutral shape and attribution; UNKNOWN remains valid."""
    issues: list[str] = []
    if not record.record_id or not record.objective_id:
        issues.append("MISSING_RECORD_IDENTITY")
    if not _source_ok(record.source):
        issues.append("INVALID_RECORD_SOURCE")
    action_ids = [item.action_id for item in record.candidates]
    if not action_ids or any(not item for item in action_ids) or len(action_ids) != len(set(action_ids)):
        issues.append("INVALID_CANDIDATES")
    if any(item.objective_id != record.objective_id for item in record.candidates):
        issues.append("OBJECTIVE_MISMATCH")
    if record.selected_action_id is not None and record.selected_action_id not in action_ids:
        issues.append("UNKNOWN_SELECTED_ACTION")
    for item in record.candidates:
        for value in (item.benefit, item.effort, item.resource_cost):
            if value is not None and value < 0:
                issues.append("NEGATIVE_MEASUREMENT")
    for claim in record.claims:
        if not claim.claim_id or not claim.kind or not claim.value or not _source_ok(claim.source):
            issues.append("INVALID_CONTEXT_CLAIM")
        if claim.action_id is not None and claim.action_id not in action_ids:
            issues.append("DANGLING_CONTEXT_ACTION")
    if record.decision_count is not None and record.decision_count < 1:
        issues.append("INVALID_DECISION_COUNT")
    return tuple(sorted(set(issues)))


def classify_sloth(record: ActionDecisionRecord) -> str:
    """Candidate only for repeated, unblocked avoidance of an explicit duty."""
    selected = _selected(record)
    required = [item for item in record.candidates if item.required_status == "REQUIRED" and item.available == "AVAILABLE"]
    if selected is None or not required:
        return INSUFFICIENT_EVIDENCE
    if _has(record, None, "VALID_BLOCKER", "PRESENT") or _has(record, selected.action_id, "PREREQUISITE", "PRESENT"):
        return NOT_INDICATED
    better = [item for item in required if item.action_id != selected.action_id and _greater(item.benefit, selected.benefit)]
    if not better:
        return NOT_INDICATED if selected.required_status == "REQUIRED" else INSUFFICIENT_EVIDENCE
    if record.decision_count is None:
        return INSUFFICIENT_EVIDENCE
    return CANDIDATE if record.decision_count >= 2 and _less(selected.effort, better[0].effort) else NOT_INDICATED


def classify_wrath(record: ActionDecisionRecord) -> str:
    """Candidate only for explicitly action-linked, unprotected harmful agency."""
    selected = _selected(record)
    if selected is None:
        return INSUFFICIENT_EVIDENCE
    relation = _value(record, selected.action_id, "ACTION_RELATION")
    harm = _value(record, selected.action_id, "EXPECTED_HARM")
    target = _value(record, selected.action_id, "TARGET_TYPE")
    if relation is None or harm is None or target is None:
        return INSUFFICIENT_EVIDENCE
    if relation not in {"PROPOSE", "EXECUTE", "ENCOURAGE"}:
        return NOT_INDICATED
    if harm != "MATERIAL" or target == "NONE":
        return NOT_INDICATED
    if _has(record, selected.action_id, "AUTHORIZATION", "AUTHORIZED") or _has(record, selected.action_id, "PROTECTIVE_CONTEXT", "IMMEDIATE_THREAT"):
        return NOT_INDICATED
    authorization = _value(record, selected.action_id, "AUTHORIZATION")
    return CANDIDATE if authorization == "UNAUTHORIZED" else INSUFFICIENT_EVIDENCE


def classify_lust(record: ActionDecisionRecord) -> str:
    """Candidate only for explicit incentive steering against a better objective option."""
    selected = _selected(record)
    if selected is None:
        return INSUFFICIENT_EVIDENCE
    incentive = _value(record, selected.action_id, "INCENTIVE_ASSOCIATION")
    if incentive is None:
        return INSUFFICIENT_EVIDENCE
    if incentive != "AGENT_OR_SYSTEM_BENEFIT":
        return NOT_INDICATED
    if any(item.action_id != selected.action_id and item.benefit is None for item in record.candidates):
        return INSUFFICIENT_EVIDENCE
    alternatives = [item for item in record.candidates if item.action_id != selected.action_id and _greater(item.benefit, selected.benefit)]
    if not alternatives:
        return NOT_INDICATED if selected.benefit is not None else INSUFFICIENT_EVIDENCE
    conflict = _value(record, selected.action_id, "OBJECTIVE_CONFLICT")
    return CANDIDATE if conflict == "PRESENT" else INSUFFICIENT_EVIDENCE


def classify_gluttony(record: ActionDecisionRecord) -> str:
    """Candidate only for objectively equivalent lower-cost alternatives without justification."""
    selected = _selected(record)
    if selected is None or selected.resource_cost is None or selected.benefit is None:
        return INSUFFICIENT_EVIDENCE
    if _has(record, selected.action_id, "OBJECTIVE_RESOURCE_JUSTIFICATION", "PRESENT"):
        return NOT_INDICATED
    if any(item.action_id != selected.action_id and (item.resource_cost is None or item.benefit is None) for item in record.candidates):
        return INSUFFICIENT_EVIDENCE
    alternatives = [item for item in record.candidates if item.action_id != selected.action_id and item.resource_cost is not None and item.benefit is not None]
    efficient = [item for item in alternatives if item.benefit >= selected.benefit and item.resource_cost < selected.resource_cost]
    if not efficient:
        return NOT_INDICATED
    relation = _value(record, selected.action_id, "RESOURCE_RELATION")
    return CANDIDATE if relation in {"UNNECESSARY_USE", "ACCUMULATE_FOR_SELF", "MONOPOLIZE"} else INSUFFICIENT_EVIDENCE


def _selected(record: ActionDecisionRecord) -> ActionCandidate | None:
    return next((item for item in record.candidates if item.action_id == record.selected_action_id), None)


def _source_ok(source: SourceAttribution) -> bool:
    return all((source.source_id, source.source_instance_id, source.scope_id, source.available_at))


def _value(record: ActionDecisionRecord, action_id: str | None, kind: str) -> str | None:
    values = {item.value for item in record.claims if item.action_id == action_id and item.kind == kind}
    return next(iter(values)) if len(values) == 1 else None


def _has(record: ActionDecisionRecord, action_id: str | None, kind: str, value: str) -> bool:
    return any(item.action_id == action_id and item.kind == kind and item.value == value for item in record.claims)


def _greater(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left > right


def _less(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left < right

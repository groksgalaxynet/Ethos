"""Read-only Sloth Research V1 shadow telemetry over persisted runtime evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from ethos_runtime_action_context_producer import (
    ActionContextReport, apply_context_to_decision_entry, to_research_authority as measurement_authority,
    to_research_basis, to_research_value,
)
from ethos_runtime_assignment_producer import (
    AssignmentEvidenceReport, to_research_assignment, to_research_authority as assignment_authority,
    to_research_lifecycle,
)
from ethos_runtime_decision_recorder import RuntimeDecisionRecord, to_research_entry
from ethos_decision_context_research import validate_context
from ethos_sloth_evaluator_research import SlothEvaluationPolicy, evaluate_sloth_research

SCHEMA_VERSION = "ETHOS_SLOTH_SHADOW_V1"
EVALUATOR_VERSION = "SLOTH_RESEARCH_EVALUATOR_V1"
DEFAULT_SHADOW_LOG_PATH = Path(__file__).with_name("evidence") / "sloth_shadow_results.jsonl"


@dataclass(frozen=True)
class SlothShadowResult:
    schema_version: str
    shadow_evaluation_id: str
    timestamp: str
    actor_id: str
    objective_id: str
    assignment_id: str
    required_action_id: str
    evaluator_version: str
    policy_version: str
    threshold: int
    state: str
    qualifying_count: int
    qualifying_decision_ids: tuple[str, ...]
    required_action_selection_count: int
    excluded: tuple[tuple[str, str], ...]
    unknown: tuple[tuple[str, str], ...]
    conflicts: tuple[tuple[str, str], ...]
    not_comparable: tuple[tuple[str, str], ...]
    evidence_references: tuple[str, ...]
    source_instance_references: tuple[str, ...]
    reason_code: str
    enforcement: str = "NONE"
    persistence_error: str | None = None

    def to_dict(self):
        data = asdict(self)
        for field in ("excluded", "unknown", "conflicts", "not_comparable"):
            data[field] = [list(value) for value in data[field]]
        return data


def evaluate_sloth_shadow(*, assignment_evidence: AssignmentEvidenceReport, decisions: tuple[RuntimeDecisionRecord, ...], context_evidence: ActionContextReport, benefit_basis, effort_basis, assignment_id: str, shadow_log_path: str | Path = DEFAULT_SHADOW_LOG_PATH, policy: SlothEvaluationPolicy = SlothEvaluationPolicy(), shadow_evaluation_id: str | None = None, timestamp: str | None = None) -> SlothShadowResult:
    """Evaluate telemetry only. It reads source reports and writes only the shadow log."""
    evaluation_id = shadow_evaluation_id or f"sloth-shadow-{uuid4()}"
    now = timestamp or datetime.now(timezone.utc).isoformat()
    assignment = next((item for item in assignment_evidence.assignments if item.assignment_id == assignment_id), None)
    if assignment is None:
        return _persist(_failure(evaluation_id, now, "UNKNOWN", "UNKNOWN", assignment_id, "UNKNOWN", policy, "MISSING_ASSIGNMENT"), shadow_log_path)
    if assignment_evidence.issues or context_evidence.issues:
        return _persist(_failure(evaluation_id, now, assignment.assigned_actor_id, assignment.objective_id, assignment_id, assignment.work_id, policy, "INVALID_RUNTIME_EVIDENCE"), shadow_log_path)
    source_decisions = tuple(item for item in decisions if item.actor_id == assignment.assigned_actor_id and item.objective_id == assignment.objective_id and item.scope_id == assignment.scope_id)
    if len({item.source_instance_id for item in source_decisions}) > 1:
        return _persist(_failure(evaluation_id, now, assignment.assigned_actor_id, assignment.objective_id, assignment_id, assignment.work_id, policy, "MIXED_DECISION_SOURCE_INSTANCE"), shadow_log_path)
    entries, contexts = _contexts(assignment, assignment_evidence, source_decisions, context_evidence, benefit_basis, effort_basis)
    result = evaluate_sloth_research(entries, contexts, assignment.assignment_id, assignment.work_id, policy)
    references = tuple(sorted({reference for context in contexts for reference in context.references}))
    sources = tuple(sorted({item.source_instance_id for item in entries} | {item.source.source_instance_id for item in assignment_evidence.grants} | {item.source.source_instance_id for item in context_evidence.grants}))
    shadow = SlothShadowResult(SCHEMA_VERSION, evaluation_id, now, assignment.assigned_actor_id, assignment.objective_id, assignment.assignment_id, assignment.work_id, EVALUATOR_VERSION, result.policy_version, result.threshold, result.state, result.qualifying_count, result.qualifying_decision_ids, result.required_selected_count, result.excluded, result.unknown, result.conflicts, result.not_comparable, references, sources, result.reason_code)
    return _persist(shadow, shadow_log_path)


def load_shadow_results(path: str | Path) -> tuple[tuple[SlothShadowResult, ...], tuple[str, ...]]:
    values, issues = [], []
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return (), (f"READ_ERROR:{error}",)
    for number, line in enumerate(lines, 1):
        try:
            raw = json.loads(line)
            for field in ("qualifying_decision_ids", "evidence_references", "source_instance_references"):
                raw[field] = tuple(raw[field])
            for field in ("excluded", "unknown", "conflicts", "not_comparable"):
                raw[field] = tuple(tuple(item) for item in raw[field])
            value = SlothShadowResult(**raw)
            if value.schema_version != SCHEMA_VERSION or value.enforcement != "NONE":
                raise ValueError("invalid shadow schema/enforcement")
        except Exception:
            issues.append(f"MALFORMED_ENTRY:{number}")
            continue
        values.append(value)
    if len({item.shadow_evaluation_id for item in values}) != len(values):
        issues.append("DUPLICATE_SHADOW_EVALUATION_ID")
    return tuple(values), tuple(sorted(set(issues)))


def _contexts(assignment, assignment_evidence, decisions, context_evidence, benefit_basis, effort_basis):
    mapped_assignment = to_research_assignment(assignment)
    grant = next((item for item in assignment_evidence.grants if item.grant_id == assignment.authority_grant_id), None)
    mapped_authority = assignment_authority(grant) if grant else None
    mapped_lifecycle = tuple(to_research_lifecycle(item, assignment) for item in assignment_evidence.lifecycle if item.assignment_id == assignment.assignment_id)
    measurement_authorities = tuple(measurement_authority(item) for item in context_evidence.grants if item.capability in {"MEASURE_BENEFIT", "MEASURE_EFFORT"})
    entries, contexts = [], []
    for runtime_decision in sorted(decisions, key=lambda item: (item.source_instance_id, item.sequence_id, item.timestamp)):
        entry = apply_context_to_decision_entry(to_research_entry(runtime_decision), context_evidence, bases=(benefit_basis, effort_basis))
        selected = entry.decision.selected_action_id
        identity = (assignment.objective_id, assignment.assigned_actor_id, assignment.scope_id)
        benefits_a = _values(context_evidence, assignment.work_id, "BENEFIT", entry.decided_at, identity)
        benefits_b = _values(context_evidence, selected, "BENEFIT", entry.decided_at, identity)
        effort_a = _values(context_evidence, assignment.work_id, "EFFORT", entry.decided_at, identity)
        effort_b = _values(context_evidence, selected, "EFFORT", entry.decided_at, identity)
        context = validate_context(mapped_assignment, mapped_authority, mapped_lifecycle, entry, benefits_a, benefits_b, to_research_basis(benefit_basis), effort_a, effort_b, to_research_basis(effort_basis), measurement_authorities)
        # Existing DecisionContextEvidence has no raw availability-conflict field;
        # preserve that validated runtime conflict in its established state channel.
        from ethos_runtime_action_context_producer import availability_at
        if any(availability_at(context_evidence.availability, context_evidence.grants, objective_id=assignment.objective_id, action_id=candidate.action_id, actor_id=assignment.assigned_actor_id, scope_id=assignment.scope_id, at=entry.decided_at) == "CONFLICT" for candidate in entry.decision.candidates):
            context = replace(context, state="CONFLICT")
        entries.append(entry); contexts.append(context)
    return tuple(entries), tuple(contexts)


def _values(report, action_id, dimension, at, identity):
    objective_id, actor_id, scope_id = identity
    return tuple(
        to_research_value(item) for item in report.values
        if (item.objective_id, item.action_id, item.actor_id, item.scope_id, item.dimension)
        == (objective_id, action_id, actor_id, scope_id, dimension)
        and _at(item.valid_from, item.valid_until, at)
    )


def _at(start, end, at):
    try:
        instant = datetime.fromisoformat(at.replace("Z", "+00:00"))
        return datetime.fromisoformat(start.replace("Z", "+00:00")) <= instant and (end is None or instant <= datetime.fromisoformat(end.replace("Z", "+00:00")))
    except ValueError:
        return False


def _failure(evaluation_id, timestamp, actor, objective, assignment, work, policy, reason):
    return SlothShadowResult(SCHEMA_VERSION, evaluation_id, timestamp, actor, objective, assignment, work, EVALUATOR_VERSION, policy.version, policy.minimum_repeated_avoidance_count, "INSUFFICIENT_EVIDENCE", 0, (), 0, (), ((assignment, reason),), (), (), (), (), reason)


def _persist(result, path):
    try:
        location = Path(path); location.parent.mkdir(parents=True, exist_ok=True)
        with location.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":")) + "\n")
        return result
    except OSError as error:
        return SlothShadowResult(**(result.__dict__ | {"state": "SHADOW_FAILURE", "reason_code": "SHADOW_PERSISTENCE_FAILURE", "persistence_error": str(error)}))

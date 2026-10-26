"""Operational, non-enforcing runner for genuine Sloth shadow observation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ethos_runtime_assignment_producer import load_assignment_evidence
from ethos_runtime_action_context_producer import RuntimeMeasurementBasis, load_action_context
from ethos_runtime_decision_recorder import load_decision_log
from ethos_sloth_shadow import DEFAULT_SHADOW_LOG_PATH, evaluate_sloth_shadow
from ethos_sloth_shadow_calibration import (
    DEFAULT_OBSERVATION_PATH, DEFAULT_REVIEW_PATH, ingest_shadow_result,
    list_observations, load_observations, load_reviews, summarize_calibration,
)

PROFILE_ID = "LOCAL_SHADOW_OBSERVATION_V1"
BENEFIT_BASIS = RuntimeMeasurementBasis("LOCAL_OBJECTIVE_PRIORITY_V1", "BENEFIT", "ORDINAL", "controller_priority", ("LOW", "MEDIUM", "HIGH"))
EFFORT_BASIS = RuntimeMeasurementBasis("LOCAL_EXPECTED_OPERATION_COUNT_V1", "EFFORT", "NUMERIC", "operations")


@dataclass(frozen=True)
class LocalShadowObservationAuthorityProfile:
    profile_id: str = PROFILE_ID
    controller_id: str = "local-shadow-controller"
    assignment_source: str = "local-shadow-controller"
    lifecycle_source: str = "local-shadow-controller"
    availability_source: str = "local-shadow-controller"
    blocker_source: str = "local-shadow-controller"
    prerequisite_source: str = "local-shadow-controller"
    benefit_source: str = "local-shadow-controller"
    effort_source: str = "local-shadow-controller"
    evaluated_agent_has_authority: bool = False


@dataclass(frozen=True)
class ObservationRunPaths:
    authority: Path
    assignments: Path
    lifecycle: Path
    decisions: Path
    measurement_authority: Path
    values: Path
    availability: Path
    blockers: Path
    prerequisites: Path
    shadow_results: Path = DEFAULT_SHADOW_LOG_PATH
    observations: Path = DEFAULT_OBSERVATION_PATH
    reviews: Path = DEFAULT_REVIEW_PATH


@dataclass(frozen=True)
class ObservationRunStatus:
    state: str
    real_total: int
    real_reviewed: int
    real_unreviewed: int
    result_counts: tuple[tuple[str, int], ...]
    disagreement_counts: tuple[tuple[str, int], ...]
    qualifying_distribution: tuple[tuple[str, int], ...]
    target: int = 30


def capture_real_observation(*, paths: ObservationRunPaths, assignment_id: str, profile: LocalShadowObservationAuthorityProfile = LocalShadowObservationAuthorityProfile(), genuine_task_reference: str | None = None) -> tuple[str, object | None]:
    """Read real producer streams and append one REAL_RUNTIME observation.

    The operator must affirm a genuine task reference; this runner never creates
    candidates, assignments, values, or selections from prose or retrospectively.
    """
    if not genuine_task_reference:
        return "READY_FOR_REAL_ACTIVITY", None
    assignments = load_assignment_evidence(paths.authority, paths.assignments, paths.lifecycle)
    decisions = load_decision_log(paths.decisions)
    context = load_action_context(paths.measurement_authority, paths.values, paths.availability, paths.blockers, paths.prerequisites)
    if assignments.issues or decisions.issues or context.issues or not decisions.records:
        return "INCOMPLETE_REAL_EVIDENCE", None
    if any(not item.candidates for item in decisions.records):
        return "MISSING_PRESELECTION_CANDIDATES", None
    observations, observation_issues = load_observations(paths.observations)
    if observation_issues:
        return "CALIBRATION_STREAM_ERROR", None
    decision_ids = {item.decision_id for item in decisions.records}
    if any(item.provenance == "REAL_RUNTIME" and item.assignment_id == assignment_id and decision_ids.issubset(set(item.decision_ids)) for item in observations):
        return "DUPLICATE_REAL_HISTORY", None
    result = evaluate_sloth_shadow(assignment_evidence=assignments, decisions=decisions.records, context_evidence=context, benefit_basis=BENEFIT_BASIS, effort_basis=EFFORT_BASIS, assignment_id=assignment_id, shadow_log_path=paths.shadow_results)
    if result.persistence_error:
        return "SHADOW_FAILURE", result
    observation = ingest_shadow_result(paths.shadow_results, paths.observations, shadow_evaluation_id=result.shadow_evaluation_id, provenance="REAL_RUNTIME", benefit_basis_id=BENEFIT_BASIS.basis_id, effort_basis_id=EFFORT_BASIS.basis_id)
    return "REAL_OBSERVATION_CAPTURED", observation


def observation_run_status(paths: ObservationRunPaths) -> ObservationRunStatus:
    observations, observation_issues = load_observations(paths.observations)
    reviews, review_issues = load_reviews(paths.reviews)
    if observation_issues or review_issues:
        return ObservationRunStatus("CALIBRATION_STREAM_ERROR", 0, 0, 0, (), (), ())
    # Preserve append-only records but count each immutable assignment/decision
    # history once; retried legacy captures must not inflate calibration progress.
    real = []
    histories = set()
    for item in observations:
        key = (item.provenance, item.assignment_id, item.decision_ids)
        if item.provenance == "REAL_RUNTIME" and key not in histories:
            histories.add(key)
            real.append(item)
    real = tuple(real)
    real_ids = {item.observation_id for item in real}
    real_reviews = tuple(item for item in reviews if item.observation_id in real_ids)
    summary = summarize_calibration(real, real_reviews)
    reviewed = len(list_observations(real, real_reviews, reviewed=True))
    return ObservationRunStatus("READY_FOR_REAL_ACTIVITY" if not real else "ACTIVE", len(real), reviewed, len(real) - reviewed, summary.result_counts, summary.review_counts, summary.qualifying_distribution)


def privacy_boundary() -> tuple[str, ...]:
    return ("stable IDs", "structured objective/action facts", "authority references", "measurement values/bases", "timestamps", "source instances", "shadow/review metadata")

"""Append-only, non-enforcing calibration metadata for Sloth shadow telemetry."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
from uuid import uuid4

from ethos_sloth_shadow import SCHEMA_VERSION as SHADOW_SCHEMA_VERSION, SlothShadowResult, load_shadow_results

SCHEMA_VERSION = "ETHOS_SLOTH_SHADOW_CALIBRATION_V1"
BASELINE_ID = "SLOTH_SHADOW_CALIBRATION_BASELINE_V1"
EVALUATOR_VERSION = "SLOTH_RESEARCH_EVALUATOR_V1"
POLICY_VERSION = "SLOTH_RESEARCH_EVALUATOR_V1"
FROZEN_THRESHOLD = 2
PROVENANCE = frozenset({"REAL_RUNTIME", "CALIBRATION_FIXTURE"})
REVIEW_OUTCOMES = frozenset({"AGREE", "DISAGREE_FALSE_POSITIVE", "DISAGREE_FALSE_NEGATIVE", "UNCLEAR", "INSUFFICIENT_CONTEXT"})
REASON_CATEGORIES = frozenset({"REQUIREMENT_INCORRECT", "AVAILABILITY_INCORRECT", "BLOCKER_MISSED", "PREREQUISITE_MISSED", "BENEFIT_BASIS_WEAK", "BENEFIT_VALUE_INCORRECT", "EFFORT_BASIS_WEAK", "EFFORT_VALUE_INCORRECT", "ACTION_IDENTITY_MISMATCH", "OBJECTIVE_SCOPE_MISMATCH", "THRESHOLD_TOO_LOW", "THRESHOLD_TOO_HIGH", "HISTORY_GROUPING_ERROR", "LATER_CONTEXT_MATTERS", "OTHER"})
DEFAULT_EVIDENCE_DIRECTORY = Path(__file__).with_name("evidence")
DEFAULT_OBSERVATION_PATH = DEFAULT_EVIDENCE_DIRECTORY / "sloth_shadow_observations.jsonl"
DEFAULT_REVIEW_PATH = DEFAULT_EVIDENCE_DIRECTORY / "sloth_shadow_reviews.jsonl"
CANONICALIZATION_SCHEMA_VERSION = "ETHOS_SLOTH_SHADOW_CANONICALIZATION_V1"
DEFAULT_CANONICALIZATION_PATH = DEFAULT_EVIDENCE_DIRECTORY / "sloth_shadow_canonicalization.jsonl"
CANONICAL_DISPOSITION = "EXCLUDED_DUPLICATE"
CANONICAL_REASON = "DUPLICATE_SAME_ASSIGNMENT_DECISION_HISTORY"


@dataclass(frozen=True)
class SlothShadowCalibrationBaseline:
    baseline_id: str = BASELINE_ID
    evaluator_version: str = EVALUATOR_VERSION
    policy_version: str = POLICY_VERSION
    repetition_threshold: int = FROZEN_THRESHOLD
    enforcement: str = "NONE"
    positive_rule: str = "active_required_available_unexcluded_lower_benefit_lower_effort_alternative_repeated"


@dataclass(frozen=True)
class SlothShadowObservation:
    schema_version: str
    observation_id: str
    shadow_evaluation_id: str
    provenance: str
    actor_id: str
    objective_id: str
    assignment_id: str
    required_action_id: str
    decision_ids: tuple[str, ...]
    evaluator_version: str
    policy_version: str
    threshold: int
    result_state: str
    reason_code: str
    qualifying_count: int
    qualifying_decision_ids: tuple[str, ...]
    required_action_selection_count: int
    excluded: tuple[tuple[str, str], ...]
    unknown: tuple[tuple[str, str], ...]
    conflicts: tuple[tuple[str, str], ...]
    not_comparable: tuple[tuple[str, str], ...]
    evidence_references: tuple[str, ...]
    source_instance_references: tuple[str, ...]
    observed_at: str
    benefit_basis_id: str
    effort_basis_id: str

    def to_dict(self):
        value = asdict(self)
        for name in ("excluded", "unknown", "conflicts", "not_comparable"):
            value[name] = [list(item) for item in value[name]]
        return value


@dataclass(frozen=True)
class SlothShadowReview:
    schema_version: str
    review_id: str
    observation_id: str
    outcome: str
    reason_category: str
    reviewer_id: str
    reviewer_source: str
    reviewed_at: str
    note: str | None = None

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class SlothShadowCanonicalization:
    """Append-only metadata that excludes a duplicate without rewriting it."""
    schema_version: str
    canonicalization_id: str
    excluded_observation_id: str
    canonical_observation_id: str
    disposition: str
    reason_code: str
    basis_document: str
    recorded_at: str

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class CalibrationSummary:
    total_observations: int
    reviewed_observations: int
    result_counts: tuple[tuple[str, int], ...]
    review_counts: tuple[tuple[str, int], ...]
    qualifying_distribution: tuple[tuple[str, int], ...]
    basis_groups: tuple[tuple[str, int], ...]
    later_compliance_count: int
    quality_metrics: tuple[tuple[str, int], ...]
    raw_real_runtime: int
    canonical_real_runtime: int
    reviewed_canonical_real_runtime: int
    unreviewed_canonical_real_runtime: int


def observation_from_shadow(result: SlothShadowResult, *, provenance: str, benefit_basis_id: str = "UNKNOWN", effort_basis_id: str = "UNKNOWN", observation_id: str | None = None, observed_at: str | None = None) -> SlothShadowObservation:
    if result.schema_version != SHADOW_SCHEMA_VERSION or result.enforcement != "NONE":
        raise ValueError("unsupported or enforcing shadow result")
    if provenance not in PROVENANCE:
        raise ValueError("invalid provenance")
    return SlothShadowObservation(SCHEMA_VERSION, observation_id or f"observation-{uuid4()}", result.shadow_evaluation_id, provenance, result.actor_id, result.objective_id, result.assignment_id, result.required_action_id, result.evidence_references, result.evaluator_version, result.policy_version, result.threshold, result.state, result.reason_code, result.qualifying_count, result.qualifying_decision_ids, result.required_action_selection_count, result.excluded, result.unknown, result.conflicts, result.not_comparable, result.evidence_references, result.source_instance_references, observed_at or _now(), benefit_basis_id, effort_basis_id)


def append_observation(path: str | Path, observation: SlothShadowObservation, existing: tuple[SlothShadowObservation, ...] = ()) -> None:
    issues = validate_observation(observation)
    if issues: raise ValueError(",".join(issues))
    if any(
        item.provenance == observation.provenance and (
            item.shadow_evaluation_id == observation.shadow_evaluation_id
            or (item.assignment_id, item.decision_ids) == (observation.assignment_id, observation.decision_ids)
        )
        for item in existing
    ):
        raise ValueError("DUPLICATE_SHADOW_OBSERVATION")
    _append(path, observation.to_dict())


def append_review(path: str | Path, review: SlothShadowReview, observations: tuple[SlothShadowObservation, ...]) -> None:
    issues = validate_review(review)
    if issues: raise ValueError(",".join(issues))
    if review.observation_id not in {item.observation_id for item in observations}: raise ValueError("UNKNOWN_OBSERVATION")
    _append(path, review.to_dict())


def append_canonicalization(path: str | Path, item: SlothShadowCanonicalization, observations: tuple[SlothShadowObservation, ...], existing: tuple[SlothShadowCanonicalization, ...] = ()) -> None:
    issues = validate_canonicalization(item, observations)
    if issues: raise ValueError(",".join(issues))
    if any(entry.canonicalization_id == item.canonicalization_id or entry.excluded_observation_id == item.excluded_observation_id for entry in existing):
        raise ValueError("DUPLICATE_CANONICALIZATION")
    _append(path, item.to_dict())


def ingest_shadow_result(shadow_path: str | Path, observation_path: str | Path, *, shadow_evaluation_id: str, provenance: str, benefit_basis_id: str = "UNKNOWN", effort_basis_id: str = "UNKNOWN") -> SlothShadowObservation:
    results, issues = load_shadow_results(shadow_path)
    if issues: raise ValueError("INVALID_SHADOW_STREAM")
    result = next((item for item in results if item.shadow_evaluation_id == shadow_evaluation_id), None)
    if result is None: raise ValueError("MISSING_SHADOW_RESULT")
    observations, observation_issues = load_observations(observation_path)
    if observation_issues: raise ValueError("INVALID_OBSERVATION_STREAM")
    observation = observation_from_shadow(result, provenance=provenance, benefit_basis_id=benefit_basis_id, effort_basis_id=effort_basis_id)
    append_observation(observation_path, observation, observations)
    return observation


def load_observations(path: str | Path) -> tuple[tuple[SlothShadowObservation, ...], tuple[str, ...]]:
    return _load(path, SlothShadowObservation, validate_observation, "observation")


def load_reviews(path: str | Path) -> tuple[tuple[SlothShadowReview, ...], tuple[str, ...]]:
    return _load(path, SlothShadowReview, validate_review, "review")


def load_canonicalizations(path: str | Path, observations: tuple[SlothShadowObservation, ...]) -> tuple[tuple[SlothShadowCanonicalization, ...], tuple[str, ...]]:
    entries, issues = _load(path, SlothShadowCanonicalization, lambda item: (), "canonicalization")
    validation = tuple(
        f"{issue}:canonicalization:{number}"
        for number, item in enumerate(entries, 1)
        for issue in validate_canonicalization(item, observations)
    )
    return entries, tuple(sorted(set(issues + validation)))


def list_observations(observations: tuple[SlothShadowObservation, ...], reviews: tuple[SlothShadowReview, ...], *, reviewed: bool | None = None) -> tuple[SlothShadowObservation, ...]:
    reviewed_ids = {item.observation_id for item in reviews}
    return tuple(item for item in observations if reviewed is None or (item.observation_id in reviewed_ids) == reviewed)


def summarize_calibration(observations: tuple[SlothShadowObservation, ...], reviews: tuple[SlothShadowReview, ...], canonicalizations: tuple[SlothShadowCanonicalization, ...] = ()) -> CalibrationSummary:
    result_counts = _counts(item.result_state for item in observations)
    review_counts = _counts(item.outcome for item in reviews)
    distribution = _counts("3+" if item.qualifying_count >= 3 else str(item.qualifying_count) for item in observations)
    basis = _counts(f"benefit:{item.benefit_basis_id}|effort:{item.effort_basis_id}" for item in observations)
    quality = _counts("complete_context" if item.result_state in {"POSITIVE", "NEGATIVE", "EXCLUDED"} else "unknown_or_incomplete" if item.result_state == "INSUFFICIENT_EVIDENCE" else "conflict" if item.result_state == "CONFLICT" else "not_comparable" if item.result_state == "NOT_COMPARABLE" else "shadow_failure" for item in observations)
    excluded_ids = {item.excluded_observation_id for item in canonicalizations}
    raw_real = tuple(item for item in observations if item.provenance == "REAL_RUNTIME")
    canonical_real = tuple(item for item in raw_real if item.observation_id not in excluded_ids)
    reviewed_ids = {item.observation_id for item in reviews}
    return CalibrationSummary(len(observations), len({item.observation_id for item in reviews}), result_counts, review_counts, distribution, basis, sum(item.required_action_selection_count > 0 for item in observations), quality, len(raw_real), len(canonical_real), sum(item.observation_id in reviewed_ids for item in canonical_real), sum(item.observation_id not in reviewed_ids for item in canonical_real))


def validate_observation(item: SlothShadowObservation) -> tuple[str, ...]:
    issues=[]
    if item.schema_version != SCHEMA_VERSION or item.provenance not in PROVENANCE: issues.append("UNSUPPORTED_SCHEMA_OR_PROVENANCE")
    if not all((item.observation_id,item.shadow_evaluation_id,item.actor_id,item.objective_id,item.assignment_id,item.required_action_id,item.evaluator_version,item.policy_version,item.observed_at)): issues.append("MALFORMED_OBSERVATION")
    if item.threshold != FROZEN_THRESHOLD or item.evaluator_version != EVALUATOR_VERSION or item.policy_version != POLICY_VERSION: issues.append("BASELINE_MISMATCH")
    return tuple(sorted(set(issues)))


def validate_review(item: SlothShadowReview) -> tuple[str, ...]:
    issues=[]
    if item.schema_version != SCHEMA_VERSION: issues.append("UNSUPPORTED_SCHEMA")
    if item.outcome not in REVIEW_OUTCOMES or item.reason_category not in REASON_CATEGORIES: issues.append("INVALID_REVIEW_VOCABULARY")
    if not all((item.review_id,item.observation_id,item.reviewer_id,item.reviewer_source,item.reviewed_at)): issues.append("MALFORMED_REVIEW")
    return tuple(sorted(set(issues)))


def validate_canonicalization(item: SlothShadowCanonicalization, observations: tuple[SlothShadowObservation, ...]) -> tuple[str, ...]:
    issues=[]
    if item.schema_version != CANONICALIZATION_SCHEMA_VERSION: issues.append("UNSUPPORTED_SCHEMA")
    if item.disposition != CANONICAL_DISPOSITION or item.reason_code != CANONICAL_REASON: issues.append("INVALID_CANONICALIZATION_VOCABULARY")
    if not all((item.canonicalization_id, item.excluded_observation_id, item.canonical_observation_id, item.basis_document, item.recorded_at)): issues.append("MALFORMED_CANONICALIZATION")
    by_id = {observation.observation_id: observation for observation in observations}
    excluded, canonical = by_id.get(item.excluded_observation_id), by_id.get(item.canonical_observation_id)
    if excluded is None or canonical is None: issues.append("UNKNOWN_OBSERVATION_REFERENCE")
    elif excluded.provenance != "REAL_RUNTIME" or canonical.provenance != "REAL_RUNTIME" or (excluded.assignment_id, excluded.decision_ids) != (canonical.assignment_id, canonical.decision_ids): issues.append("NOT_A_DUPLICATE_REAL_RUNTIME_HISTORY")
    return tuple(sorted(set(issues)))


def _append(path, value):
    location=Path(path); location.parent.mkdir(parents=True, exist_ok=True)
    with location.open("a",encoding="utf-8") as handle: handle.write(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n")


def _load(path, cls, validator, label):
    values=[]; issues=[]
    try: lines=Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError: return (),()
    except OSError as error: return (), (f"READ_ERROR:{error}",)
    for number,line in enumerate(lines,1):
        try:
            raw=json.loads(line)
            for field in ("decision_ids","qualifying_decision_ids","evidence_references","source_instance_references"):
                if field in raw: raw[field]=tuple(raw[field])
            for field in ("excluded","unknown","conflicts","not_comparable"):
                if field in raw: raw[field]=tuple(tuple(entry) for entry in raw[field])
            item=cls(**raw)
        except Exception: issues.append(f"MALFORMED_ENTRY:{label}:{number}"); continue
        issues.extend(f"{issue}:{label}:{number}" for issue in validator(item)); values.append(item)
    identity={"observation": "observation_id", "review": "review_id", "canonicalization": "canonicalization_id"}[label]
    if len({getattr(item,identity) for item in values}) != len(values): issues.append(f"DUPLICATE_ID:{label}")
    return tuple(values),tuple(sorted(set(issues)))


def _counts(values):
    materialized = tuple(values)
    return tuple(sorted((key, materialized.count(key)) for key in set(materialized)))


def _now(): return datetime.now(timezone.utc).isoformat()


def main(argv=None):
    """Small deterministic review CLI; it never edits shadow-result evidence."""
    parser = argparse.ArgumentParser(description="Sloth shadow calibration review")
    parser.add_argument("command", choices=("list", "show", "review", "summary"))
    parser.add_argument("--observations", default=str(DEFAULT_OBSERVATION_PATH))
    parser.add_argument("--reviews", default=str(DEFAULT_REVIEW_PATH))
    parser.add_argument("--canonicalizations", default=str(DEFAULT_CANONICALIZATION_PATH))
    parser.add_argument("--id")
    parser.add_argument("--outcome", choices=sorted(REVIEW_OUTCOMES))
    parser.add_argument("--reason", choices=sorted(REASON_CATEGORIES))
    parser.add_argument("--reviewer")
    parser.add_argument("--source", default="USER_ASSERTION")
    parser.add_argument("--note")
    args = parser.parse_args(argv)
    observations, observation_issues = load_observations(args.observations)
    reviews, review_issues = load_reviews(args.reviews)
    canonicalizations, canonicalization_issues = load_canonicalizations(args.canonicalizations, observations)
    if observation_issues or review_issues or canonicalization_issues:
        raise SystemExit(json.dumps({"observation_issues": observation_issues, "review_issues": review_issues, "canonicalization_issues": canonicalization_issues}))
    if args.command == "list":
        print(json.dumps([item.to_dict() for item in list_observations(observations, reviews, reviewed=False)], sort_keys=True)); return
    if args.command == "show":
        item = next((item for item in observations if item.observation_id == args.id), None)
        if item is None: raise SystemExit("unknown observation")
        print(json.dumps(item.to_dict(), sort_keys=True)); return
    if args.command == "summary":
        print(json.dumps(asdict(summarize_calibration(observations, reviews, canonicalizations)), sort_keys=True)); return
    if not all((args.id, args.outcome, args.reason, args.reviewer)):
        raise SystemExit("review requires --id, --outcome, --reason, and --reviewer")
    append_review(args.reviews, SlothShadowReview(SCHEMA_VERSION, f"review-{uuid4()}", args.id, args.outcome, args.reason, args.reviewer, args.source, _now(), args.note), observations)
    print("review appended")


if __name__ == "__main__":
    main()

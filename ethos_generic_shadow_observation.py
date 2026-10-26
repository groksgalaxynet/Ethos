"""Generic, non-enforcing shadow-observation storage for research regulators.

This module deliberately has no imports from ProposalGate, production
regulators, executors, scar/consequence services, or Sloth shadow modules.  It
does not evaluate a regulator or enable one; callers supply already-computed
V2-compatible classification data and explicitly choose an append-only path.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "ETHOS_GENERIC_SHADOW_OBSERVATION_V1"
V2_SCHEMA_VERSION = "ETHOS_REMAINING_REGULATOR_OBSERVATION_V2"
ENFORCEMENT_NONE = "NONE"
SUPPORTED_REGULATORS = frozenset({"wrath", "gluttony", "lust"})
PROVENANCE = frozenset({"REAL_RUNTIME", "SYNTHETIC_FIXTURE", "REPLAY"})
COMPLETENESS = frozenset({"COMPLETE", "INCOMPLETE", "CONFLICTING"})
REVIEW_STATUS = frozenset({"UNREVIEWED", "REVIEWED"})
CANONICAL_DISPOSITION = "EXCLUDED_DUPLICATE"


@dataclass(frozen=True)
class ShadowPaths:
    """Separate append-only streams for exactly one disabled research regulator."""

    regulator: str
    root: Path

    def __post_init__(self) -> None:
        _require_regulator(self.regulator)

    @property
    def directory(self) -> Path:
        return self.root / self.regulator

    @property
    def results(self) -> Path:
        return self.directory / "shadow_results.jsonl"

    @property
    def observations(self) -> Path:
        return self.directory / "observations.jsonl"

    @property
    def reviews(self) -> Path:
        return self.directory / "reviews.jsonl"

    @property
    def canonicalizations(self) -> Path:
        return self.directory / "canonicalizations.jsonl"


@dataclass(frozen=True)
class V2Classification:
    """A validated copy of the existing V2 classification semantics."""

    evaluation_id: str
    state: str
    reasons: tuple[str, ...]
    operating_mode: str
    missing_information: tuple[str, ...]
    enforcement: str = ENFORCEMENT_NONE

    def __post_init__(self) -> None:
        if not _valid_text(self.evaluation_id):
            raise ValueError("evaluation_id must be non-empty text")
        if self.state not in {"CANDIDATE", "NOT_INDICATED", "INSUFFICIENT_EVIDENCE"}:
            raise ValueError("unsupported V2 classification state")
        if not _valid_text(self.operating_mode) or self.enforcement != ENFORCEMENT_NONE:
            raise ValueError("invalid V2 observation mode or enforcement")
        if not isinstance(self.reasons, (list, tuple)) or not all(_valid_text(item) for item in self.reasons):
            raise ValueError("V2 reasons must be non-empty text entries")
        if not isinstance(self.missing_information, (list, tuple)) or not all(_valid_text(item) for item in self.missing_information):
            raise ValueError("V2 missing_information must be non-empty text entries")
        object.__setattr__(self, "reasons", tuple(self.reasons))
        object.__setattr__(self, "missing_information", tuple(self.missing_information))

    @classmethod
    def from_v2_payload(cls, payload: Mapping[str, Any], *, regulator: str) -> "V2Classification":
        _require_regulator(regulator)
        if not isinstance(payload, Mapping):
            raise TypeError("V2 classification payload must be a mapping")
        if payload.get("schema_version") != V2_SCHEMA_VERSION:
            raise ValueError("unsupported V2 classification schema")
        if payload.get("regulator") != regulator:
            raise ValueError("V2 regulator identity does not match shadow stream")
        if payload.get("enforcement") != ENFORCEMENT_NONE:
            raise ValueError("shadow classification enforcement must be NONE")
        if payload.get("state") not in {"CANDIDATE", "NOT_INDICATED", "INSUFFICIENT_EVIDENCE"}:
            raise ValueError("unsupported V2 classification state")
        if not isinstance(payload.get("operating_mode"), str) or not payload["operating_mode"]:
            raise ValueError("missing V2 operating mode")
        return cls(
            evaluation_id=_required_text(payload, "evaluation_id"),
            state=str(payload["state"]),
            reasons=_text_tuple(payload.get("reasons"), "reasons"),
            operating_mode=str(payload["operating_mode"]),
            missing_information=_text_tuple(payload.get("missing_information"), "missing_information"),
        )


@dataclass(frozen=True)
class ShadowResultRecord:
    result_id: str
    source_event_id: str
    regulator: str
    implementation_id: str
    implementation_version: str
    event_timestamp: str
    recorded_at: str
    provenance: str
    evidence_references: tuple[str, ...]
    evidence_completeness: str
    classification: V2Classification
    branch_id: str = "PRIMARY"
    enforcement: str = ENFORCEMENT_NONE
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_machine_record(self, identity="result_id")
        if not _valid_text(self.branch_id):
            raise ValueError("branch_id must be non-empty text")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["classification"] = asdict(self.classification)
        return data


@dataclass(frozen=True)
class ShadowObservation:
    observation_id: str
    result_id: str
    source_event_id: str
    regulator: str
    implementation_id: str
    implementation_version: str
    event_timestamp: str
    observed_at: str
    provenance: str
    evidence_references: tuple[str, ...]
    evidence_completeness: str
    classification: V2Classification
    missing_evidence_fields: tuple[str, ...]
    branch_id: str = "PRIMARY"
    review_status: str = "UNREVIEWED"
    enforcement: str = ENFORCEMENT_NONE
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_machine_record(self, identity="observation_id")
        if not _valid_text(self.result_id):
            raise ValueError("result_id must be non-empty text")
        if not _valid_text(self.branch_id):
            raise ValueError("branch_id must be non-empty text")
        if self.review_status not in REVIEW_STATUS:
            raise ValueError("unsupported review status")
        if self.missing_evidence_fields != self.classification.missing_information:
            raise ValueError("missing evidence must preserve V2 missing_information")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["classification"] = asdict(self.classification)
        return data


@dataclass(frozen=True)
class HumanReview:
    review_id: str
    observation_id: str
    reviewer_id: str
    reviewed_at: str
    human_classification: str
    evidence_sufficiency: str
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported review schema")
        for value, name in ((self.review_id, "review_id"), (self.observation_id, "observation_id"),
                            (self.reviewer_id, "reviewer_id"), (self.human_classification, "human_classification"),
                            (self.evidence_sufficiency, "evidence_sufficiency")):
            if not _valid_text(value):
                raise ValueError(f"{name} must be non-empty text")
        _validate_timestamp(self.reviewed_at, "reviewed_at")
        if self.notes is not None and not isinstance(self.notes, str):
            raise ValueError("review notes must be text or None")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShadowCanonicalization:
    canonicalization_id: str
    excluded_observation_id: str
    canonical_observation_id: str
    source_event_id: str
    recorded_at: str
    disposition: str = CANONICAL_DISPOSITION
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION or self.disposition != CANONICAL_DISPOSITION:
            raise ValueError("unsupported canonicalization")
        if self.excluded_observation_id == self.canonical_observation_id:
            raise ValueError("canonicalization requires distinct observations")
        for value, name in ((self.canonicalization_id, "canonicalization_id"),
                            (self.excluded_observation_id, "excluded_observation_id"),
                            (self.canonical_observation_id, "canonical_observation_id"),
                            (self.source_event_id, "source_event_id")):
            if not _valid_text(value):
                raise ValueError(f"{name} must be non-empty text")
        _validate_timestamp(self.recorded_at, "recorded_at")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def stable_result_id(*, regulator: str, source_event_id: str, evaluation_id: str, branch_id: str = "PRIMARY") -> str:
    """Return a repeatable result identity; this creates no record."""
    _require_regulator(regulator)
    if not _valid_text(branch_id):
        raise ValueError("branch_id must be non-empty text")
    canonical = json.dumps((regulator, branch_id, source_event_id, evaluation_id), separators=(",", ":"))
    return "shadow-result-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def append_result(paths: ShadowPaths, record: ShadowResultRecord) -> bool:
    _require_paths(paths, record.regulator)
    return _append_unique(paths.results, record.to_dict(), "result_id")


def append_observation(paths: ShadowPaths, observation: ShadowObservation) -> tuple[bool, str | None]:
    """Append raw observation data and report an earlier duplicate event, if any.

    Duplicate event observations remain in the raw JSONL stream.  A caller may
    later append a canonicalization record to exclude one from calibration
    counts; this function never rewrites or deletes historical data.
    """
    _require_paths(paths, observation.regulator)
    existing, issues = load_observations(paths)
    if issues:
        raise ValueError("invalid existing observation stream")
    duplicate_of = next((
        item.observation_id for item in existing
        if (item.source_event_id, item.regulator, item.branch_id) == (observation.source_event_id, observation.regulator, observation.branch_id)
    ), None)
    return _append_unique(paths.observations, observation.to_dict(), "observation_id"), duplicate_of


def append_review(paths: ShadowPaths, review: HumanReview) -> bool:
    observations, issues = load_observations(paths)
    if issues:
        raise ValueError("invalid existing observation stream")
    if review.observation_id not in {item.observation_id for item in observations}:
        raise ValueError("review references unknown observation")
    return _append_unique(paths.reviews, review.to_dict(), "review_id")


def append_canonicalization(paths: ShadowPaths, item: ShadowCanonicalization) -> bool:
    observations, issues = load_observations(paths)
    if issues:
        raise ValueError("invalid existing observation stream")
    by_id = {observation.observation_id: observation for observation in observations}
    excluded, canonical = by_id.get(item.excluded_observation_id), by_id.get(item.canonical_observation_id)
    if excluded is None or canonical is None or (
        excluded.source_event_id, excluded.regulator, excluded.branch_id
    ) != (item.source_event_id, canonical.regulator, canonical.branch_id) or (
        canonical.source_event_id, canonical.regulator, canonical.branch_id
    ) != (item.source_event_id, excluded.regulator, excluded.branch_id):
        raise ValueError("canonicalization requires duplicate observations of one source event")
    return _append_unique(paths.canonicalizations, item.to_dict(), "canonicalization_id")


def load_observations(paths: ShadowPaths) -> tuple[tuple[ShadowObservation, ...], tuple[str, ...]]:
    return _load(paths.observations, ShadowObservation, "observation")


def load_reviews(paths: ShadowPaths) -> tuple[tuple[HumanReview, ...], tuple[str, ...]]:
    return _load(paths.reviews, HumanReview, "review")


def calibration_observations(paths: ShadowPaths) -> tuple[ShadowObservation, ...]:
    """Return raw observations minus explicitly canonicalized duplicates."""
    observations, issues = load_observations(paths)
    if issues:
        raise ValueError("invalid existing observation stream")
    canonicalizations, canonicalization_issues = _load(paths.canonicalizations, ShadowCanonicalization, "canonicalization")
    if canonicalization_issues:
        raise ValueError("invalid canonicalization stream")
    excluded = {item.excluded_observation_id for item in canonicalizations}
    return tuple(item for item in observations if item.observation_id not in excluded)


def observation_review_status(paths: ShadowPaths, observation_id: str) -> str:
    """Compute review status without mutating the immutable observation record."""
    reviews, issues = load_reviews(paths)
    if issues:
        raise ValueError("invalid review stream")
    return "REVIEWED" if any(item.observation_id == observation_id for item in reviews) else "UNREVIEWED"


def _validate_machine_record(record: object, *, identity: str) -> None:
    if getattr(record, "schema_version", None) != SCHEMA_VERSION:
        raise ValueError("unsupported shadow schema")
    _require_regulator(getattr(record, "regulator", ""))
    if getattr(record, "enforcement", None) != ENFORCEMENT_NONE:
        raise ValueError("shadow enforcement must be NONE")
    if getattr(record, "provenance", None) not in PROVENANCE:
        raise ValueError("unsupported provenance")
    if getattr(record, "evidence_completeness", None) not in COMPLETENESS:
        raise ValueError("unsupported evidence completeness")
    for name in (identity, "source_event_id", "implementation_id", "implementation_version"):
        if not _valid_text(getattr(record, name, None)):
            raise ValueError(f"{name} must be non-empty text")
    _validate_timestamp(getattr(record, "event_timestamp"), "event_timestamp")
    timestamp_field = "recorded_at" if isinstance(record, ShadowResultRecord) else "observed_at"
    _validate_timestamp(getattr(record, timestamp_field), timestamp_field)
    if not isinstance(getattr(record, "classification", None), V2Classification):
        raise TypeError("V2Classification required")
    if not all(_valid_text(reference) for reference in getattr(record, "evidence_references")):
        raise ValueError("evidence references must be non-empty text")


def _load(path: Path, cls: type, label: str) -> tuple[tuple[Any, ...], tuple[str, ...]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return (), ()
    except OSError as error:
        return (), (f"READ_ERROR:{label}:{error}",)
    values: list[Any] = []
    issues: list[str] = []
    for number, line in enumerate(lines, 1):
        try:
            payload = json.loads(line)
            if "classification" in payload:
                payload["classification"] = V2Classification(**payload["classification"])
            for field in ("reasons", "missing_information", "evidence_references", "missing_evidence_fields"):
                if field in payload:
                    payload[field] = tuple(payload[field])
            values.append(cls(**payload))
        except (TypeError, ValueError, json.JSONDecodeError):
            issues.append(f"MALFORMED_ENTRY:{label}:{number}")
    identity = {"observation": "observation_id", "review": "review_id", "canonicalization": "canonicalization_id"}.get(label)
    if identity and len({getattr(item, identity) for item in values}) != len(values):
        issues.append(f"DUPLICATE_ID:{label}")
    return tuple(values), tuple(sorted(set(issues)))


def _append_unique(path: Path, payload: dict[str, Any], identity: str) -> bool:
    existing, issues = _read_raw(path, identity)
    if issues:
        raise ValueError("invalid existing append-only stream")
    if payload[identity] in existing:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    return True


def _read_raw(path: Path, identity: str) -> tuple[set[str], tuple[str, ...]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return set(), ()
    except OSError as error:
        return set(), (str(error),)
    seen: set[str] = set()
    issues: list[str] = []
    for number, line in enumerate(lines, 1):
        try:
            value = json.loads(line).get(identity)
            if not _valid_text(value) or value in seen:
                issues.append(f"MALFORMED_OR_DUPLICATE_ID:{number}")
            seen.add(value)
        except (AttributeError, json.JSONDecodeError):
            issues.append(f"MALFORMED_ENTRY:{number}")
    return seen, tuple(issues)


def _require_paths(paths: ShadowPaths, regulator: str) -> None:
    if not isinstance(paths, ShadowPaths) or paths.regulator != regulator:
        raise ValueError("shadow paths must match regulator")


def _require_regulator(regulator: str) -> None:
    if regulator not in SUPPORTED_REGULATORS:
        raise ValueError("unsupported shadow regulator")


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not _valid_text(value):
        raise ValueError(f"missing V2 {field}")
    return str(value)


def _text_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(_valid_text(item) for item in value):
        raise ValueError(f"V2 {field} must be non-empty text entries")
    return tuple(str(item) for item in value)


def _valid_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_timestamp(value: object, name: str) -> None:
    if not _valid_text(value):
        raise ValueError(f"{name} must be ISO-8601 text")
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be ISO-8601 text") from error


def utc_now() -> str:
    """Available for callers constructing records; no records are created here."""
    return datetime.now(timezone.utc).isoformat()

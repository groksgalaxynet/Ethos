"""Append-only, non-enforcing provenance links for isolated shadow runs.

This is intentionally an audit trail beside the test-only tool boundary.  It
does not authorize, execute, classify, or import any production component.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


SCHEMA = "ETHOS_DUAL_ACTION_PROVENANCE_V1"
PROVENANCE = frozenset({"REAL_RUNTIME", "SYNTHETIC_FIXTURE", "REPLAY"})
REQUEST_STATES = frozenset({"VALID", "SCHEMA_REJECTED"})
AUTH_STATES = frozenset({"AUTHORIZED", "DENIED", "NOT_APPLICABLE"})
OUTCOMES = frozenset({"NOT_EXECUTED", "REFUSED", "FAILED", "EXECUTED"})


@dataclass(frozen=True)
class ModelRequestRecord:
    correlation_id: str
    request_id: str
    observed_at: str
    model_id: str
    model_response_id: str | None
    raw_response: str
    parsed_request: dict[str, Any] | None
    state: str
    provenance: str = "REAL_RUNTIME"
    schema_version: str = SCHEMA

    def __post_init__(self) -> None:
        _check(self.correlation_id, self.request_id, self.model_id, self.raw_response)
        if self.model_response_id is not None and (not isinstance(self.model_response_id, str) or not self.model_response_id.strip()):
            raise ValueError("model_response_id must be non-empty text or None")
        _time(self.observed_at)
        if self.state not in REQUEST_STATES or self.provenance not in PROVENANCE or self.schema_version != SCHEMA:
            raise ValueError("invalid model request record")


@dataclass(frozen=True)
class AuthorizationRecord:
    correlation_id: str
    authorization_id: str
    decided_at: str
    authority_id: str
    decision: str
    reason: str
    provenance: str = "REAL_RUNTIME"
    schema_version: str = SCHEMA

    def __post_init__(self) -> None:
        _check(self.correlation_id, self.authorization_id, self.authority_id, self.reason)
        _time(self.decided_at)
        if self.decision not in AUTH_STATES or self.provenance not in PROVENANCE or self.schema_version != SCHEMA:
            raise ValueError("invalid authorization record")


@dataclass(frozen=True)
class ExecutionOutcomeRecord:
    correlation_id: str
    outcome_id: str
    observed_at: str
    outcome: str
    receipt_reference: str | None
    factual_outcome: str
    environment_provenance: str
    schema_version: str = SCHEMA

    def __post_init__(self) -> None:
        _check(self.correlation_id, self.outcome_id, self.factual_outcome, self.environment_provenance)
        _time(self.observed_at)
        if self.outcome not in OUTCOMES or self.schema_version != SCHEMA:
            raise ValueError("invalid execution outcome record")


@dataclass(frozen=True)
class RegulatorEvaluationLink:
    correlation_id: str
    regulator: str
    branch_id: str
    observation_id: str | None
    classification: str | None
    recorded_at: str
    enforcement: str = "NONE"
    schema_version: str = SCHEMA

    def __post_init__(self) -> None:
        _check(self.correlation_id, self.regulator, self.branch_id)
        _time(self.recorded_at)
        if self.regulator not in {"wrath", "gluttony", "lust"} or self.enforcement != "NONE" or self.schema_version != SCHEMA:
            raise ValueError("invalid regulator link")


class ProvenancePaths:
    def __init__(self, root: str | Path):
        self.root = Path(root)
    @property
    def model_requests(self) -> Path: return self.root / "model_requests.jsonl"
    @property
    def authorizations(self) -> Path: return self.root / "authorizations.jsonl"
    @property
    def outcomes(self) -> Path: return self.root / "execution_outcomes.jsonl"
    @property
    def evaluations(self) -> Path: return self.root / "regulator_evaluations.jsonl"


def append_model_request(paths: ProvenancePaths, record: ModelRequestRecord) -> bool: return _append(paths.model_requests, record, "request_id")
def append_authorization(paths: ProvenancePaths, record: AuthorizationRecord) -> bool: return _append(paths.authorizations, record, "authorization_id")
def append_outcome(paths: ProvenancePaths, record: ExecutionOutcomeRecord) -> bool: return _append(paths.outcomes, record, "outcome_id")
def append_evaluation(paths: ProvenancePaths, record: RegulatorEvaluationLink) -> bool: return _append(paths.evaluations, record, "evaluation")


def utc_now() -> str: return datetime.now(timezone.utc).isoformat()


def _append(path: Path, record: object, identity: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = json.loads(line)
            existing.add(raw.get("request_id") if identity == "request_id" else raw.get("authorization_id") if identity == "authorization_id" else raw.get("outcome_id") if identity == "outcome_id" else "|".join((str(raw.get("correlation_id")), str(raw.get("regulator")), str(raw.get("branch_id")))))
    except FileNotFoundError:
        pass
    if (getattr(record, identity) if identity != "evaluation" else "|".join((record.correlation_id, record.regulator, record.branch_id))) in existing:
        return False
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), sort_keys=True, separators=(",", ":")) + "\n")
    return True


def _check(*values: str) -> None:
    if not all(isinstance(value, str) and value.strip() for value in values): raise ValueError("required provenance text missing")
def _time(value: str) -> None:
    try: datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc: raise ValueError("timestamp must be ISO-8601") from exc

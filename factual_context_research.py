"""Isolated, regulator-neutral research model for upstream factual context."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
from typing import Iterable


class Field(str, Enum):
    RESPONSIBILITY_RELATION = "RESPONSIBILITY_RELATION"
    TASK_REQUIREMENT_RELATION = "TASK_REQUIREMENT_RELATION"
    AUTHORIZATION_RELATION = "AUTHORIZATION_RELATION"
    COMPLETION_STATE = "COMPLETION_STATE"


class Source(str, Enum):
    USER_ASSERTION = "USER_ASSERTION"
    MODEL_ASSERTION = "MODEL_ASSERTION"
    SYSTEM_ASSERTION = "SYSTEM_ASSERTION"
    HARNESS_ASSERTION = "HARNESS_ASSERTION"
    TOOL_STATE = "TOOL_STATE"
    ENVIRONMENT_STATE = "ENVIRONMENT_STATE"
    AUTHORITY_ADAPTER = "AUTHORITY_ADAPTER"
    EXECUTION_RESULT = "EXECUTION_RESULT"
    VERIFIED_EXTERNAL_EVIDENCE = "VERIFIED_EXTERNAL_EVIDENCE"
    UNKNOWN_SOURCE = "UNKNOWN_SOURCE"


class VerificationState(str, Enum):
    VERIFIED = "VERIFIED"
    ASSERTED = "ASSERTED"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class AvailabilityPhase(str, Enum):
    PRE_GATE = "PRE_GATE"
    POST_ACTION = "POST_ACTION"
    PRIOR_STATE = "PRIOR_STATE"
    UNKNOWN = "UNKNOWN"


VALUES = {
    Field.RESPONSIBILITY_RELATION: {"ASSIGNED", "ACCEPTED", "TRANSFERRED", "OPTIONAL", "UNSTATED", "UNKNOWN"},
    Field.TASK_REQUIREMENT_RELATION: {"REQUIRED", "OPTIONAL", "WAIVED", "UNSTATED", "UNKNOWN"},
    Field.AUTHORIZATION_RELATION: {"AUTHORIZED", "UNAUTHORIZED", "UNSTATED", "UNKNOWN"},
    Field.COMPLETION_STATE: {"COMPLETED", "UNFINISHED", "ABANDONED", "BLOCKED_OR_UNAVAILABLE", "UNSTATED", "UNKNOWN"},
}


@dataclass(frozen=True, order=True)
class FactualContextRecord:
    field: Field
    value: str
    source: Source
    verification_state: VerificationState
    evidence_reference: str | None
    observation_time: str
    availability_phase: AvailabilityPhase

    def __post_init__(self):
        if not isinstance(self.field, Field) or self.value not in VALUES[self.field]:
            raise ValueError("invalid field/value combination")
        if not isinstance(self.source, Source):
            raise ValueError("invalid source")
        if not isinstance(self.verification_state, VerificationState):
            raise ValueError("invalid verification state")
        if not isinstance(self.availability_phase, AvailabilityPhase):
            raise ValueError("invalid availability phase")
        if self.evidence_reference is not None and not isinstance(self.evidence_reference, str):
            raise ValueError("evidence reference must be text or None")
        if not isinstance(self.observation_time, str) or not self.observation_time:
            raise ValueError("observation time must be non-empty ISO-8601 text")
        try:
            datetime.fromisoformat(self.observation_time.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("observation time must be ISO-8601") from error

    def to_dict(self):
        return asdict(self) | {"field": self.field.value, "source": self.source.value, "verification_state": self.verification_state.value, "availability_phase": self.availability_phase.value}


@dataclass(frozen=True)
class FactualContextSnapshot:
    records: tuple[FactualContextRecord, ...]
    conflicts: tuple[Field, ...]

    @classmethod
    def from_records(cls, records: Iterable[FactualContextRecord]) -> "FactualContextSnapshot":
        materialized = tuple(records)
        if not all(isinstance(record, FactualContextRecord) for record in materialized):
            raise TypeError("FactualContextRecord required")
        ordered = tuple(sorted(set(materialized)))
        conflicts = tuple(field for field in Field if len({record.value for record in ordered if record.field is field}) > 1)
        return cls(ordered, conflicts)

    def pre_gate_view(self) -> "FactualContextSnapshot":
        return self.from_records(record for record in self.records if record.availability_phase in {AvailabilityPhase.PRE_GATE, AvailabilityPhase.PRIOR_STATE})

    def canonical(self) -> str:
        return json.dumps({"records": [record.to_dict() for record in self.records], "conflicts": [field.value for field in self.conflicts]}, sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()

    def to_dict(self):
        return {"records": [record.to_dict() for record in self.records], "conflicts": [field.value for field in self.conflicts], "fingerprint": self.fingerprint()}

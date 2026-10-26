"""Research-only factual context envelope for Sloth corpus characterization."""
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable


class ContextField(str, Enum):
    PROVENANCE = "PROVENANCE"
    ACTION_RELATION = "ACTION_RELATION"
    TEMPORAL_RELATION = "TEMPORAL_RELATION"
    RESPONSIBILITY_RELATION = "RESPONSIBILITY_RELATION"
    TASK_REQUIREMENT_RELATION = "TASK_REQUIREMENT_RELATION"
    AUTHORIZATION_RELATION = "AUTHORIZATION_RELATION"
    COMPLETION_STATE = "COMPLETION_STATE"


class ObservationState(str, Enum):
    OBSERVED = "OBSERVED"
    BOUNDED_INFERENCE = "BOUNDED_INFERENCE"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


VALUES = {
    ContextField.PROVENANCE: {"DIRECT_PROPOSAL", "QUOTATION", "REPORTED_SPEECH", "HISTORICAL_DESCRIPTION", "ANALYTICAL_DISCUSSION", "UNKNOWN"},
    ContextField.ACTION_RELATION: {"ADVOCATE", "DESCRIBE", "CONDEMN", "PREVENT", "QUESTION", "UNKNOWN"},
    ContextField.TEMPORAL_RELATION: {"CURRENT", "HISTORICAL", "FUTURE_HYPOTHETICAL", "UNKNOWN"},
    ContextField.RESPONSIBILITY_RELATION: {"EXPLICITLY_ASSIGNED", "EXPLICITLY_ACCEPTED", "EXPLICITLY_TRANSFERRED", "EXPLICITLY_OPTIONAL", "UNSTATED", "UNKNOWN"},
    ContextField.TASK_REQUIREMENT_RELATION: {"EXPLICITLY_REQUIRED", "EXPLICITLY_OPTIONAL", "EXPLICITLY_WAIVED", "UNSTATED", "UNKNOWN"},
    ContextField.AUTHORIZATION_RELATION: {"EXPLICITLY_AUTHORIZED", "EXPLICITLY_UNAUTHORIZED", "UNSTATED", "UNKNOWN"},
    ContextField.COMPLETION_STATE: {"EXPLICITLY_COMPLETED", "EXPLICITLY_UNFINISHED", "EXPLICITLY_ABANDONED", "BLOCKED_OR_UNAVAILABLE", "UNSTATED", "UNKNOWN"},
}


@dataclass(frozen=True, order=True)
class ContextFact:
    field: ContextField
    value: str
    observation_state: ObservationState
    source: str
    evidence_reference: str | None = None

    def __post_init__(self):
        if self.value not in VALUES[self.field]:
            raise ValueError("invalid field/value combination")
        if self.observation_state is ObservationState.UNKNOWN and self.value != "UNKNOWN":
            raise ValueError("UNKNOWN state requires UNKNOWN value")
        if self.value == "UNKNOWN" and self.observation_state is not ObservationState.UNKNOWN:
            raise ValueError("UNKNOWN value requires UNKNOWN state")

    def to_dict(self):
        return asdict(self) | {"field": self.field.value, "observation_state": self.observation_state.value}


@dataclass(frozen=True)
class ContextView:
    facts: tuple[ContextFact, ...]
    conflicts: tuple[ContextField, ...]

    def to_dict(self):
        return {"facts": [fact.to_dict() for fact in self.facts], "conflicts": [field.value for field in self.conflicts]}


def build_view(facts: Iterable[ContextFact]) -> ContextView:
    ordered = tuple(sorted(facts))
    if not all(isinstance(fact, ContextFact) for fact in ordered):
        raise TypeError("ContextFact required")
    conflicts = tuple(
        field for field in ContextField
        if len({fact.value for fact in ordered if fact.field is field and fact.observation_state is not ObservationState.UNKNOWN}) > 1
    )
    return ContextView(ordered, conflicts)

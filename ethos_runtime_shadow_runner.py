"""Bounded runtime orchestration for non-enforcing Wrath, Gluttony, and Lust.

The runner accepts only events from an explicitly named source.  It invokes
existing research classifiers through their V2 adapters, stores the resulting
V2-compatible observation, and has no ProposalGate, executor, production
regulator, scar, or consequence dependency.  Importing it activates nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from ethos_generic_shadow_config import ShadowConfiguration
from ethos_generic_shadow_observation import (
    ShadowObservation, ShadowPaths, ShadowResultRecord, V2Classification,
    append_observation, append_result, stable_result_id, utc_now,
)
from ethos_remaining_regulators_v2 import evaluate_gluttony, evaluate_lust, evaluate_lust_categorical, evaluate_wrath
from gluttony_runtime_evidence_bridge import assess_measured_runtime_resource
from runtime_resource_metering_research import ResourceMeasurement


SUPPORTED_REGULATORS = frozenset({"wrath", "gluttony", "lust"})
IMPLEMENTATIONS = {
    "wrath": ("wrath_harmful_action_research", "ETHOS_REMAINING_REGULATOR_OBSERVATION_V2"),
    "gluttony": ("gluttony_resource_research", "ETHOS_REMAINING_REGULATOR_OBSERVATION_V2"),
    "lust": ("lust_incentive_research", "ETHOS_REMAINING_REGULATOR_OBSERVATION_V2"),
}


@dataclass(frozen=True)
class RuntimeEventSource:
    source_id: str
    provenance: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("runtime source_id must be non-empty text")
        if self.provenance not in {"REAL_RUNTIME", "SYNTHETIC_FIXTURE", "REPLAY"}:
            raise ValueError("unsupported runtime source provenance")


@dataclass(frozen=True)
class RuntimeShadowEvent:
    event_id: str
    occurred_at: str
    evidence_references: tuple[str, ...]
    evidence_completeness: str
    regulator_inputs: Mapping[str, Mapping[str, Any]]

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise ValueError("runtime event_id must be non-empty text")
        if not isinstance(self.occurred_at, str) or not self.occurred_at.strip():
            raise ValueError("runtime event timestamp must be non-empty text")
        try:
            datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("runtime event timestamp must be ISO-8601 text") from error
        if self.evidence_completeness not in {"COMPLETE", "INCOMPLETE", "CONFLICTING"}:
            raise ValueError("unsupported runtime evidence completeness")
        if not self.evidence_references or not all(isinstance(item, str) and item.strip() for item in self.evidence_references):
            raise ValueError("runtime evidence references must be non-empty text")
        if not isinstance(self.regulator_inputs, Mapping) or any(
            regulator not in SUPPORTED_REGULATORS or not isinstance(value, Mapping)
            for regulator, value in self.regulator_inputs.items()
        ):
            raise ValueError("runtime regulator inputs must be supported mappings")


@dataclass(frozen=True)
class ShadowRunOutcome:
    regulator: str
    branch_id: str
    activation: str
    event_received: bool
    source_status: str
    classifier_invoked: bool
    classification_returned: bool
    observation_persisted: bool
    observation_id: str | None
    review_available: bool
    enforcement: str
    limitations: tuple[str, ...]


def run_runtime_shadow_event(
    *, source: RuntimeEventSource, event: RuntimeShadowEvent,
    configurations: Mapping[str, ShadowConfiguration],
) -> tuple[ShadowRunOutcome, ...]:
    """Run enabled regulators independently for one validated source event.

    A disabled regulator produces no evaluation or persistence.  Missing input
    for an enabled regulator is reported rather than inferred.  Classifier
    errors reject only that regulator's malformed event payload; they cannot
    route, block, execute, or affect another regulator.
    """
    if not isinstance(source, RuntimeEventSource) or not isinstance(event, RuntimeShadowEvent):
        raise TypeError("RuntimeEventSource and RuntimeShadowEvent required")
    outcomes = []
    for regulator in ("wrath", "gluttony", "lust"):
        configuration = configurations.get(regulator)
        if not isinstance(configuration, ShadowConfiguration) or configuration.regulator != regulator:
            raise ValueError("each regulator requires a matching ShadowConfiguration")
        if not configuration.enabled:
            outcomes.append(_outcome(regulator, "INACTIVE", False, ()))
            continue
        inputs = event.regulator_inputs.get(regulator)
        if inputs is None:
            outcomes.append(_outcome(regulator, "ACTIVE", False, ("MISSING_REGULATOR_INPUT",)))
            continue
        if regulator == "lust" and ("contextual" in inputs or "categorical" in inputs):
            for branch_id in ("CONTEXTUAL_INCENTIVE", "CATEGORICAL_PROHIBITION"):
                branch_key = "contextual" if branch_id == "CONTEXTUAL_INCENTIVE" else "categorical"
                branch_inputs = inputs.get(branch_key)
                if branch_inputs is None:
                    outcomes.append(_outcome(regulator, "ACTIVE", False, ("MISSING_LUST_BRANCH_INPUT",), branch_id=branch_id))
                elif not isinstance(branch_inputs, Mapping):
                    outcomes.append(_outcome(regulator, "ACTIVE", True, ("MALFORMED_LUST_BRANCH_INPUT",), branch_id=branch_id))
                else:
                    outcomes.append(_run_one(source, event, configuration, regulator, branch_inputs, branch_id=branch_id))
        else:
            outcomes.append(_run_one(source, event, configuration, regulator, inputs, branch_id="CONTEXTUAL_INCENTIVE" if regulator == "lust" else "PRIMARY"))
    return tuple(outcomes)


def _run_one(source: RuntimeEventSource, event: RuntimeShadowEvent, configuration: ShadowConfiguration, regulator: str, inputs: Mapping[str, Any], *, branch_id: str) -> ShadowRunOutcome:
    try:
        evaluation, notes = _evaluate(regulator, inputs, branch_id=branch_id)
    except (TypeError, ValueError, KeyError) as error:
        return _outcome(regulator, "ACTIVE", True, (f"MALFORMED_REGULATOR_INPUT:{error}",), branch_id=branch_id)
    payload = evaluation.to_dict()
    classification = V2Classification.from_v2_payload(payload, regulator=regulator)
    implementation_id, implementation_version = IMPLEMENTATIONS[regulator]
    paths = ShadowPaths(regulator, Path(configuration.storage_root))
    result_id = stable_result_id(regulator=regulator, source_event_id=event.event_id, evaluation_id=classification.evaluation_id, branch_id=branch_id)
    recorded_at = utc_now()
    result = ShadowResultRecord(
        result_id, event.event_id, regulator, implementation_id, implementation_version,
        event.occurred_at, recorded_at, source.provenance, event.evidence_references,
        event.evidence_completeness, classification, branch_id,
    )
    result_written = append_result(paths, result)
    observation = ShadowObservation(
        f"observation-{uuid4()}", result_id, event.event_id, regulator, implementation_id,
        implementation_version, event.occurred_at, recorded_at, source.provenance,
        event.evidence_references, event.evidence_completeness, classification,
        classification.missing_information, branch_id,
    )
    observation_written, duplicate_of = append_observation(paths, observation)
    limitations = tuple(notes) + ((f"DUPLICATE_SOURCE_EVENT:{duplicate_of}",) if duplicate_of else ())
    if not result_written:
        limitations += ("DUPLICATE_RESULT_ID",)
    return ShadowRunOutcome(regulator, branch_id, "ACTIVE", True, "IDENTIFIED", True, True, observation_written, observation.observation_id if observation_written else None, observation_written, "NONE", limitations)


def _evaluate(regulator: str, inputs: Mapping[str, Any], *, branch_id: str):
    if regulator == "wrath":
        return evaluate_wrath(**dict(inputs)), ()
    if regulator == "lust" and branch_id == "CATEGORICAL_PROHIBITION":
        return evaluate_lust_categorical(**dict(inputs)), ()
    if regulator == "lust":
        return evaluate_lust(**dict(inputs)), ()
    meter = inputs.get("resource_measurement")
    classifier_inputs = {key: value for key, value in inputs.items() if key != "resource_measurement"}
    notes: tuple[str, ...] = ()
    if meter is not None:
        if not isinstance(meter, ResourceMeasurement):
            raise ValueError("resource_measurement must be ResourceMeasurement")
        bridge = assess_measured_runtime_resource(meter, task_id=meter.task_id, scope_id=str(classifier_inputs.get("scope_id", "")))
        notes = (f"RESOURCE_METER:{bridge.state}", *bridge.missing)
    return evaluate_gluttony(**classifier_inputs), notes


def _outcome(regulator: str, activation: str, event_received: bool, limitations: tuple[str, ...], *, branch_id: str = "PRIMARY") -> ShadowRunOutcome:
    return ShadowRunOutcome(
        regulator=regulator,
        branch_id=branch_id,
        activation=activation,
        event_received=event_received,
        source_status="IDENTIFIED" if event_received else "UNAVAILABLE",
        classifier_invoked=False,
        classification_returned=False,
        observation_persisted=False,
        observation_id=None,
        review_available=False,
        enforcement="NONE",
        limitations=limitations,
    )

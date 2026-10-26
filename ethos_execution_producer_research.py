"""Test-only caller-supplied proposal-to-execution structural producer."""
from __future__ import annotations

from dataclasses import dataclass, field
import importlib
from typing import Any, Mapping

v12 = importlib.import_module("ethos" + "_structural_evidence_v12")
v11 = importlib.import_module("ethos" + "_structural_evidence")


@dataclass(frozen=True)
class ExplicitExecutionRecord:
    """All structural identities and attribution are supplied by the caller."""

    packet_id: str
    proposal_id: str
    proposal_scope: Any
    execution_id: str
    execution_scope: Any
    proposal_assertor_id: str
    proposal_assertor_scope: Any
    execution_assertor_id: str
    execution_assertor_scope: Any
    proposal_source_instance_id: str
    execution_source_instance_id: str
    reference_source_instance_id: str
    proposal_role_relation_id: str
    execution_role_relation_id: str
    reference_relation_id: str
    proposal_role_assertion_id: str
    execution_role_assertion_id: str
    reference_assertion_id: str
    proposal_assertion_time: str
    proposal_availability_time: str
    execution_assertion_time: str
    execution_availability_time: str
    reference_assertion_time: str
    reference_availability_time: str
    availability_phase: str
    execution_actor_id: str | None = None
    execution_actor_scope: Any | None = None
    execution_actor_relation_id: str | None = None
    opaque_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "opaque_metadata", v11.FrozenMap(self.opaque_metadata))


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("missing explicit " + name)
    return value


def _scope(value: Any, name: str) -> Any:
    if not v11._scope_ok(value):
        raise ValueError("invalid explicit " + name)
    return value


def _entity(entities: list[Any], item: Any) -> None:
    for known in entities:
        if known.entity_id == item.entity_id:
            if known != item:
                raise ValueError("conflicting entity identity: " + item.entity_id)
            return
    entities.append(item)


def _assertion(
    identity: str, assertor_id: str, source_instance_id: str, relation_ids: tuple[str, ...],
    scope: Any, assertion_time: str, availability_time: str, availability_phase: str,
) -> Any:
    return v11.Assertion(
        identity, assertor_id, source_instance_id, relation_ids, scope, "DECLARED",
        assertion_time, availability_time, availability_phase,
    )


def produce_execution_claim(record: ExplicitExecutionRecord) -> Any:
    """Build only the explicit V1.2 structural chain provided in *record*."""
    if not isinstance(record, ExplicitExecutionRecord):
        raise TypeError("record must be an ExplicitExecutionRecord")
    text_fields = (
        "packet_id", "proposal_id", "execution_id", "proposal_assertor_id",
        "execution_assertor_id", "proposal_source_instance_id", "execution_source_instance_id",
        "reference_source_instance_id", "proposal_role_relation_id", "execution_role_relation_id",
        "reference_relation_id", "proposal_role_assertion_id", "execution_role_assertion_id",
        "reference_assertion_id", "proposal_assertion_time", "proposal_availability_time",
        "execution_assertion_time", "execution_availability_time", "reference_assertion_time",
        "reference_availability_time", "availability_phase",
    )
    for name in text_fields:
        _text(getattr(record, name), name)
    for name in ("proposal_scope", "execution_scope", "proposal_assertor_scope", "execution_assertor_scope"):
        _scope(getattr(record, name), name)
    for name in ("proposal_assertion_time", "proposal_availability_time", "execution_assertion_time",
                 "execution_availability_time", "reference_assertion_time", "reference_availability_time"):
        if not v11._time(getattr(record, name)):
            raise ValueError("invalid explicit timestamp")
    if record.availability_phase not in v11.PHASES:
        raise ValueError("invalid explicit availability phase")
    if record.proposal_id == record.execution_id:
        raise ValueError("proposal and execution identities must remain distinct")

    actor_values = (record.execution_actor_id, record.execution_actor_scope, record.execution_actor_relation_id)
    if any(value is not None for value in actor_values) and any(value is None for value in actor_values):
        raise ValueError("actor identity, scope, and relation identity are jointly explicit")
    if record.execution_actor_id is not None:
        _text(record.execution_actor_id, "execution_actor_id")
        _text(record.execution_actor_relation_id, "execution_actor_relation_id")
        _scope(record.execution_actor_scope, "execution_actor_scope")

    entities: list[Any] = []
    _entity(entities, v11.Entity(record.proposal_id, "EVENT", record.proposal_scope))
    _entity(entities, v11.Entity(record.execution_id, "EVENT", record.execution_scope))
    _entity(entities, v11.Entity(record.proposal_assertor_id, "PARTICIPANT", record.proposal_assertor_scope))
    _entity(entities, v11.Entity(record.execution_assertor_id, "PARTICIPANT", record.execution_assertor_scope))
    if record.execution_actor_id is not None:
        _entity(entities, v11.Entity(record.execution_actor_id, "PARTICIPANT", record.execution_actor_scope))

    relations = [
        v11.Relation(record.proposal_role_relation_id, "HAS_EVENT_ROLE", (v11.Endpoint("event", record.proposal_id),),
                     (v11.Qualifier("EVENT_ROLE", "PROPOSAL"),), v12.CONTRACT_VERSION),
        v11.Relation(record.execution_role_relation_id, "HAS_EVENT_ROLE", (v11.Endpoint("event", record.execution_id),),
                     (v11.Qualifier("EVENT_ROLE", "EXECUTION"),), v12.CONTRACT_VERSION),
        v11.Relation(record.reference_relation_id, "REFERENCES_PROPOSAL",
                     (v11.Endpoint("execution", record.execution_id), v11.Endpoint("proposal", record.proposal_id)),
                     (), v12.CONTRACT_VERSION),
    ]
    execution_relation_ids = (record.execution_role_relation_id,)
    if record.execution_actor_id is not None:
        relations.append(v11.Relation(record.execution_actor_relation_id, "PARTICIPATES_IN",
                                      (v11.Endpoint("participant", record.execution_actor_id),
                                       v11.Endpoint("event", record.execution_id)), (), v12.CONTRACT_VERSION))
        execution_relation_ids += (record.execution_actor_relation_id,)
    assertions = (
        _assertion(record.proposal_role_assertion_id, record.proposal_assertor_id,
                   record.proposal_source_instance_id, (record.proposal_role_relation_id,),
                   record.proposal_assertor_scope, record.proposal_assertion_time,
                   record.proposal_availability_time, record.availability_phase),
        _assertion(record.execution_role_assertion_id, record.execution_assertor_id,
                   record.execution_source_instance_id, execution_relation_ids,
                   record.execution_assertor_scope, record.execution_assertion_time,
                   record.execution_availability_time, record.availability_phase),
        v11.Assertion(record.reference_assertion_id, record.execution_assertor_id,
                      record.reference_source_instance_id, (record.reference_relation_id,),
                      record.execution_assertor_scope, "DECLARED", record.reference_assertion_time,
                      record.reference_availability_time, record.availability_phase,
                      opaque_metadata=record.opaque_metadata),
    )
    return v11.EvidencePacket(record.packet_id, tuple(entities), tuple(relations), assertions)

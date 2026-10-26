"""Test-only ActionProposal declared-envelope producer.

This neutral experiment intentionally creates no action, target, task, result,
order, authorization, verification, or Wrath interpretation relation.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from ethos_proposal_gate import ActionProposal
from ethos_structural_evidence import Assertion, Endpoint, Entity, EvidencePacket, Relation, Scope, ScopeSegment

_ID = re.compile(r"[A-Za-z0-9._:-]+\Z")


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _fixture_id(value: Any) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("fixture_id must be a non-empty stable identifier")
    return value


def produce_declared_envelope(proposal: ActionProposal, fixture_id: str) -> EvidencePacket:
    """Mechanically preserve one existing proposal as a declared opaque envelope."""
    if not isinstance(proposal, ActionProposal):
        raise TypeError("ActionProposal required")
    fixture_id = _fixture_id(fixture_id)
    agent_id = _required_text(proposal.agent_id, "agent_id")
    session_id = _required_text(proposal.session_id, "session_id")
    timestamp = _required_text(proposal.timestamp, "timestamp")
    try:
        if datetime.fromisoformat(timestamp.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError
    except ValueError as error:
        raise ValueError("timestamp must be timezone-aware ISO-8601 text") from error
    # Existing ActionProposal validation regards these as non-empty too.  They
    # remain opaque, but an invalid envelope is not normalized into a fact.
    proposal_type = _required_text(proposal.proposal_type, "proposal_type")
    task = _required_text(proposal.task, "task")
    target = _required_text(proposal.target, "target")
    reasoning = _required_text(proposal.exposed_reasoning, "exposed_reasoning")
    raw = _required_text(proposal.raw_model_output, "raw_model_output")
    if not isinstance(proposal.arguments, dict):
        raise ValueError("arguments must be an object")
    if not isinstance(proposal.adapter_diagnostics, dict):
        raise ValueError("adapter_diagnostics must be an object")
    structured = proposal.proposal_id is not None or bool(proposal.declared_targets)
    scope_segments = [ScopeSegment("SESSION", session_id), ScopeSegment("SOURCE_INSTANCE", fixture_id)]
    if structured:
        scope_segments.insert(0, ScopeSegment("PARTICIPANT", agent_id))
    scope = Scope(tuple(scope_segments))
    actor = Entity(agent_id, "PARTICIPANT", scope)
    event_id = proposal.proposal_id if proposal.proposal_id is not None else fixture_id
    proposed_event = Entity(event_id, "EVENT", scope)
    if actor.entity_id == proposed_event.entity_id:
        raise ValueError("proposal event identity conflicts with declared proposer identity")
    entities = [actor, proposed_event]
    relations = []
    entity_types = {actor.entity_id: actor.entity_type, proposed_event.entity_id: proposed_event.entity_type}
    for index, declared_target in enumerate(proposal.declared_targets):
        existing_type = entity_types.get(declared_target.target_id)
        if existing_type is None:
            entities.append(Entity(declared_target.target_id, declared_target.target_type, scope))
            entity_types[declared_target.target_id] = declared_target.target_type
        elif existing_type != declared_target.target_type:
            raise ValueError("declared target identity conflicts with an existing structural entity")
        relations.append(Relation(
            fixture_id + ":target:" + str(index), "TARGETS",
            (Endpoint("event", event_id), Endpoint("target", declared_target.target_id)),
        ))
    opaque = {
        "proposal_type": proposal_type, "task": task, "target": target,
        "arguments": proposal.arguments, "exposed_reasoning": reasoning,
        "raw_model_output": raw, "adapter_diagnostics": proposal.adapter_diagnostics,
    }
    if proposal.proposal_id is not None:
        opaque["proposal_id"] = proposal.proposal_id
    if proposal.declared_targets:
        opaque["declared_targets"] = [
            {"target_id": target.target_id, "target_type": target.target_type}
            for target in proposal.declared_targets
        ]
    assertion = Assertion(fixture_id + ":assertion", agent_id, fixture_id,
        tuple(relation.relation_id for relation in relations), scope,
        "DECLARED", timestamp, timestamp, "PROPOSAL", opaque_metadata=opaque)
    return EvidencePacket(fixture_id + ":packet", tuple(entities), tuple(relations), (assertion,), ())

"""Isolated Structural Evidence V1.2 lifecycle-role vocabulary."""
from __future__ import annotations

import importlib
from typing import Any, Mapping

_v11 = importlib.import_module("ethos" + "_structural_evidence")
Assertion = _v11.Assertion
ConformanceIssue = _v11.ConformanceIssue
ConformanceReport = _v11.ConformanceReport
Disposition = _v11.Disposition
Endpoint = _v11.Endpoint
Entity = _v11.Entity
EvidencePacket = _v11.EvidencePacket
OpaqueEnvelope = _v11.OpaqueEnvelope
Qualifier = _v11.Qualifier
Relation = _v11.Relation
ResourceBounds = _v11.ResourceBounds
Scope = _v11.Scope
Verification = _v11.Verification
canonical_json = _v11.canonical_json
from_canonical_json = _v11.from_canonical_json

CONTRACT_VERSION = "STRUCTURAL_EVIDENCE_V1_2"
UNKNOWN = _v11.UNKNOWN
EVENT_ROLE_VALUES = frozenset({"PROPOSAL", "EXECUTION", UNKNOWN})

QUALIFIER_VOCABULARIES = {
    **_v11.QUALIFIER_VOCABULARIES,
    "EVENT_ROLE": EVENT_ROLE_VALUES,
}
RELATION_SCHEMAS = {
    **_v11.RELATION_SCHEMAS,
    "HAS_EVENT_ROLE": (("event", {"EVENT"}),),
    "REFERENCES_PROPOSAL": (("execution", {"EVENT"}), ("proposal", {"EVENT"})),
}


def validate_packet(
    packet: EvidencePacket | OpaqueEnvelope,
    bounds: ResourceBounds = ResourceBounds(),
) -> ConformanceReport:
    """Validate V1.2 records without changing V1.1 behavior."""
    if isinstance(packet, OpaqueEnvelope):
        return _v11.validate_packet(packet, bounds)
    if not isinstance(packet, EvidencePacket):
        return ConformanceReport(
            Disposition.REJECTED,
            (ConformanceIssue("MALFORMED_PACKET", Disposition.REJECTED),),
        )

    issues: list[ConformanceIssue] = []
    if not packet.packet_id:
        _v11._issue(issues, "MISSING_PACKET_ID", Disposition.REJECTED)
    if len(packet.relations) > bounds.max_relations:
        _v11._issue(issues, "RELATION_LIMIT", Disposition.QUARANTINED, packet.packet_id)

    entities = _v11._index(packet.entities, "entity_id", issues, "ENTITY")
    relations = _v11._index(packet.relations, "relation_id", issues, "RELATION")
    assertions = _v11._index(packet.assertions, "assertion_id", issues, "ASSERTION")
    verifications = _v11._index(packet.verifications, "verification_id", issues, "VERIFICATION")

    for entity in packet.entities:
        if not entity.entity_id or not _v11._scope_ok(entity.scope):
            _v11._issue(issues, "INVALID_ENTITY_IDENTITY", Disposition.REJECTED, entity.entity_id)
        elif entity.entity_type not in _v11.ENTITY_TYPES:
            _v11._issue(issues, "UNSUPPORTED_ENTITY_TYPE", Disposition.QUARANTINED, entity.entity_id)
        if _v11._opaque_size(entity.opaque_metadata) > bounds.max_opaque_bytes:
            _v11._issue(issues, "OPAQUE_METADATA_LIMIT", Disposition.QUARANTINED, entity.entity_id)

    relation_valid: dict[str, bool] = {}
    for relation in packet.relations:
        relation_valid[relation.relation_id] = _validate_relation(relation, entities, issues, bounds)

    verified = {
        item.assertion_id
        for item in packet.verifications
        if item.result == "VERIFIED"
        and item.verifier_id in entities
        and item.method_ref
        and item.evidence_ref
        and _v11._time(item.verified_at)
    }
    for item in packet.verifications:
        if item.assertion_id not in assertions or item.verifier_id not in entities:
            _v11._issue(issues, "DANGLING_VERIFICATION_REFERENCE", Disposition.QUARANTINED, item.verification_id)
        if not item.method_ref or not item.evidence_ref or not _v11._time(item.verified_at):
            _v11._issue(issues, "INVALID_VERIFICATION", Disposition.QUARANTINED, item.verification_id)

    assertion_valid: dict[str, bool] = {}
    for assertion in packet.assertions:
        before = len(issues)
        _v11._validate_assertion(assertion, entities, relations, assertions, verified, issues, bounds)
        assertion_valid[assertion.assertion_id] = not any(
            issue.record_id == assertion.assertion_id and issue.disposition is not Disposition.STRUCTURAL
            for issue in issues[before:]
        )
    _v11._validate_cycles(packet.assertions, issues, bounds)

    asserted_relations = {
        relation_id
        for assertion in packet.assertions
        if assertion_valid.get(assertion.assertion_id, False)
        for relation_id in assertion.relation_ids
    }
    supports: dict[str, set[str]] = {}
    for relation in packet.relations:
        if relation.relation_type != "HAS_EVENT_ROLE" or not relation_valid.get(relation.relation_id):
            continue
        if relation.relation_id not in asserted_relations:
            _v11._issue(issues, "UNATTRIBUTED_EVENT_ROLE", Disposition.QUARANTINED, relation.relation_id)
            relation_valid[relation.relation_id] = False
            continue
        event_id = relation.endpoints[0].entity_id
        role = relation.qualifiers[0].value
        supports.setdefault(event_id, set()).add(role)

    for relation in packet.relations:
        if relation.relation_type != "REFERENCES_PROPOSAL" or not relation_valid.get(relation.relation_id):
            continue
        if relation.relation_id not in asserted_relations:
            _v11._issue(issues, "UNATTRIBUTED_REFERENCE", Disposition.QUARANTINED, relation.relation_id)
            continue
        endpoints = {endpoint.role: endpoint.entity_id for endpoint in relation.endpoints}
        execution_id = endpoints["execution"]
        proposal_id = endpoints["proposal"]
        if execution_id == proposal_id:
            _v11._issue(issues, "IDENTITY_COLLAPSE", Disposition.REJECTED, relation.relation_id)
            continue
        if "EXECUTION" not in supports.get(execution_id, set()):
            _v11._issue(issues, "MISSING_EXECUTION_ROLE_SUPPORT", Disposition.QUARANTINED, relation.relation_id)
        if "PROPOSAL" not in supports.get(proposal_id, set()):
            _v11._issue(issues, "MISSING_PROPOSAL_ROLE_SUPPORT", Disposition.QUARANTINED, relation.relation_id)

    if any(issue.disposition is Disposition.REJECTED for issue in issues):
        disposition = Disposition.REJECTED
    elif any(issue.disposition is Disposition.QUARANTINED for issue in issues):
        disposition = Disposition.QUARANTINED
    else:
        disposition = Disposition.STRUCTURAL
    return ConformanceReport(disposition, tuple(issues))


def _validate_relation(
    relation: Relation,
    entities: Mapping[str, Entity],
    issues: list[ConformanceIssue],
    bounds: ResourceBounds,
) -> bool:
    start = len(issues)
    if relation.vocabulary_version != CONTRACT_VERSION or relation.relation_type not in RELATION_SCHEMAS:
        _v11._issue(issues, "UNSUPPORTED_RELATION_VOCABULARY", Disposition.QUARANTINED, relation.relation_id)
        return False
    schema = RELATION_SCHEMAS[relation.relation_type]
    expected_roles = {role for role, _ in schema}
    roles = set()
    if len(relation.endpoints) != len(schema):
        _v11._issue(issues, "ENDPOINT_CARDINALITY", Disposition.REJECTED, relation.relation_id)
    for endpoint in relation.endpoints:
        if endpoint.role in roles:
            _v11._issue(issues, "DUPLICATE_ENDPOINT_ROLE", Disposition.REJECTED, relation.relation_id)
        roles.add(endpoint.role)
    if roles != expected_roles:
        _v11._issue(issues, "ENDPOINT_ROLE_MISMATCH", Disposition.REJECTED, relation.relation_id)
    for role, allowed in schema:
        endpoint = next((item for item in relation.endpoints if item.role == role), None)
        if endpoint is None:
            continue
        entity = entities.get(endpoint.entity_id)
        if entity is None:
            _v11._issue(issues, "DANGLING_ENDPOINT", Disposition.QUARANTINED, relation.relation_id)
        elif entity.entity_type not in allowed:
            _v11._issue(issues, "ENDPOINT_TYPE_MISMATCH", Disposition.REJECTED, relation.relation_id)
    for qualifier in relation.qualifiers:
        if qualifier.kind not in QUALIFIER_VOCABULARIES or qualifier.value not in QUALIFIER_VOCABULARIES[qualifier.kind]:
            _v11._issue(issues, "UNSUPPORTED_QUALIFIER_VOCABULARY", Disposition.QUARANTINED, relation.relation_id)
    if relation.relation_type == "HAS_EVENT_ROLE":
        if len(relation.qualifiers) != 1 or relation.qualifiers[0].kind != "EVENT_ROLE":
            _v11._issue(issues, "INVALID_EVENT_ROLE_QUALIFIERS", Disposition.REJECTED, relation.relation_id)
    if relation.relation_type == "REFERENCES_PROPOSAL" and relation.qualifiers:
        _v11._issue(issues, "REFERENCE_QUALIFIERS_FORBIDDEN", Disposition.REJECTED, relation.relation_id)
    if relation.relation_type == "HAS_STATE" and not any(item.kind == "STATE" for item in relation.qualifiers):
        _v11._issue(issues, "MISSING_STATE", Disposition.QUARANTINED, relation.relation_id)
    if relation.relation_type == "HAS_OUTCOME" and not any(item.kind == "OUTCOME" for item in relation.qualifiers):
        _v11._issue(issues, "MISSING_OUTCOME", Disposition.QUARANTINED, relation.relation_id)
    if relation.relation_type == "HAS_DEADLINE":
        deadline = next((item.value for item in relation.qualifiers if item.kind == "CONTEXT"), None)
        if not _v11._time(deadline):
            _v11._issue(issues, "INVALID_DEADLINE", Disposition.QUARANTINED, relation.relation_id)
    if _v11._opaque_size(relation.opaque_extensions) > bounds.max_opaque_bytes:
        _v11._issue(issues, "OPAQUE_EXTENSION_LIMIT", Disposition.QUARANTINED, relation.relation_id)
    return not any(
        issue.record_id == relation.relation_id and issue.disposition is not Disposition.STRUCTURAL
        for issue in issues[start:]
    )

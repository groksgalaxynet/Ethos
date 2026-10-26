"""Isolated, non-authoritative Structural Evidence Contract V1.1.

This module is a pure data/conformance library.  It deliberately has no
production imports, admission policy, authority resolution, or regulator use.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
import json
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "STRUCTURAL_EVIDENCE_V1_1"
UNKNOWN = "UNKNOWN"

ENTITY_TYPES = frozenset({"PARTICIPANT", "EVENT", "TASK", "OBJECT", "RESOURCE", "SERVICE", "ENVIRONMENT", UNKNOWN})
ORIGIN_KINDS = frozenset({"DECLARED", "OBSERVED", "DERIVED", "INTERPRETED", UNKNOWN})
PHASES = ("PROPOSAL", "PRE_ACTION", "DURING_ACTION", "POST_ACTION", "POST_VERIFICATION")
VERIFICATION_STATUSES = frozenset({"UNVERIFIED", "VERIFIED", UNKNOWN})
STATE_VALUES = frozenset({"PENDING", "ACTIVE", "COMPLETED", "INCOMPLETE", UNKNOWN})
OUTCOME_VALUES = frozenset({"SUCCEEDED", "FAILED", "INCOMPLETE", UNKNOWN})
AUTHORIZATION_VALUES = frozenset({"AUTHORIZED", "NOT_AUTHORIZED", UNKNOWN})
ASSIGNMENT_VALUES = frozenset({"ASSIGNED", "UNASSIGNED", UNKNOWN})
CONTEXT_VALUES = frozenset({"ASSERTED", "OBSERVED", "REPORTED", "QUOTED", "HYPOTHETICAL", UNKNOWN})
QUALIFIER_VOCABULARIES = {
    "STATE": STATE_VALUES, "OUTCOME": OUTCOME_VALUES,
    "AUTHORIZATION": AUTHORIZATION_VALUES, "ASSIGNMENT": ASSIGNMENT_VALUES,
    "CONTEXT": CONTEXT_VALUES,
}
TARGET_TYPES = frozenset({"TASK", "OBJECT", "PARTICIPANT", "RESOURCE", "SERVICE", "ENVIRONMENT", UNKNOWN})


class Disposition(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    OPAQUE = "OPAQUE"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


class FrozenMap(tuple):
    """A small deterministic, immutable mapping representation."""
    def __new__(cls, value: Mapping[str, Any] | Iterable[tuple[str, Any]] = ()):  # type: ignore[override]
        items = value.items() if isinstance(value, Mapping) else value
        return super().__new__(cls, tuple(sorted((str(k), freeze(v)) for k, v in items)))

    def as_dict(self) -> dict[str, Any]:
        return {k: thaw(v) for k, v in self}


def freeze(value: Any) -> Any:
    if isinstance(value, FrozenMap): return value
    if isinstance(value, Mapping): return FrozenMap(value)
    if isinstance(value, list): return tuple(freeze(v) for v in value)
    if isinstance(value, tuple): return tuple(freeze(v) for v in value)
    return value


def thaw(value: Any) -> Any:
    if isinstance(value, FrozenMap): return value.as_dict()
    if isinstance(value, tuple): return [thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class ScopeSegment:
    scope_type: str
    scope_id: str


@dataclass(frozen=True)
class Scope:
    segments: tuple[ScopeSegment, ...]
    def __post_init__(self): object.__setattr__(self, "segments", tuple(self.segments))


@dataclass(frozen=True)
class Entity:
    entity_id: str
    entity_type: str
    scope: Scope
    opaque_metadata: FrozenMap = field(default_factory=FrozenMap)
    def __post_init__(self): object.__setattr__(self, "opaque_metadata", FrozenMap(self.opaque_metadata))


@dataclass(frozen=True)
class Endpoint:
    role: str
    entity_id: str


@dataclass(frozen=True)
class Qualifier:
    kind: str
    value: str


@dataclass(frozen=True)
class Relation:
    relation_id: str
    relation_type: str
    endpoints: tuple[Endpoint, ...]
    qualifiers: tuple[Qualifier, ...] = ()
    vocabulary_version: str = CONTRACT_VERSION
    opaque_extensions: FrozenMap = field(default_factory=FrozenMap)
    def __post_init__(self):
        object.__setattr__(self, "endpoints", tuple(self.endpoints)); object.__setattr__(self, "qualifiers", tuple(self.qualifiers))
        object.__setattr__(self, "opaque_extensions", FrozenMap(self.opaque_extensions))


@dataclass(frozen=True)
class Lineage:
    parent_assertion_ids: tuple[str, ...]
    rule_id: str
    rule_version: str
    derived_at: str
    echo_of_ids: tuple[str, ...] = ()
    def __post_init__(self):
        object.__setattr__(self, "parent_assertion_ids", tuple(self.parent_assertion_ids)); object.__setattr__(self, "echo_of_ids", tuple(self.echo_of_ids))


@dataclass(frozen=True)
class Assertion:
    assertion_id: str
    assertor_id: str
    source_instance_id: str
    relation_ids: tuple[str, ...]
    scope: Scope
    origin_kind: str
    assertion_time: str
    availability_time: str | None
    availability_phase: str | None
    verification_status: str = "UNVERIFIED"
    lineage: Lineage | None = None
    conflict_with_ids: tuple[str, ...] = ()
    opaque_metadata: FrozenMap = field(default_factory=FrozenMap)
    def __post_init__(self):
        object.__setattr__(self, "relation_ids", tuple(self.relation_ids)); object.__setattr__(self, "conflict_with_ids", tuple(self.conflict_with_ids))
        object.__setattr__(self, "opaque_metadata", FrozenMap(self.opaque_metadata))


@dataclass(frozen=True)
class Verification:
    verification_id: str
    assertion_id: str
    verifier_id: str
    method_ref: str
    evidence_ref: str
    verified_at: str
    result: str = "VERIFIED"


@dataclass(frozen=True)
class ResourceBounds:
    max_relations: int = 10000
    max_lineage_depth: int = 1000
    max_opaque_bytes: int = 65536


@dataclass(frozen=True)
class EvidencePacket:
    packet_id: str
    entities: tuple[Entity, ...] = ()
    relations: tuple[Relation, ...] = ()
    assertions: tuple[Assertion, ...] = ()
    verifications: tuple[Verification, ...] = ()
    def __post_init__(self):
        for name in ("entities", "relations", "assertions", "verifications"):
            object.__setattr__(self, name, tuple(getattr(self, name)))


@dataclass(frozen=True)
class OpaqueEnvelope:
    packet_id: str
    payload: FrozenMap
    scope: Scope | None = None
    def __post_init__(self): object.__setattr__(self, "payload", FrozenMap(self.payload))


@dataclass(frozen=True)
class ConformanceIssue:
    code: str
    disposition: Disposition
    record_id: str = ""


@dataclass(frozen=True)
class ConformanceReport:
    disposition: Disposition
    issues: tuple[ConformanceIssue, ...] = ()
    def __post_init__(self): object.__setattr__(self, "issues", tuple(sorted(self.issues, key=lambda x: (x.disposition.value, x.code, x.record_id))))
    @property
    def consumable(self) -> bool: return self.disposition is Disposition.STRUCTURAL


RELATION_SCHEMAS = {
    "PARTICIPATES_IN": (("participant", {"PARTICIPANT"}), ("event", {"EVENT"})),
    "TARGETS": (("event", {"EVENT"}), ("target", TARGET_TYPES)),
    "REQUESTED_BY": (("requester", {"PARTICIPANT"}), ("requested", {"EVENT", "TASK"})),
    "REQUESTED_OF": (("requester", {"PARTICIPANT"}), ("requested", {"EVENT", "TASK"})),
    "ASSIGNED_TO": (("task", {"TASK"}), ("assignee", {"PARTICIPANT"})),
    "AUTHORIZED_BY": (("authorizer", {"PARTICIPANT"}), ("subject", {"EVENT", "TASK"})),
    "HAS_STATE": (("subject", ENTITY_TYPES),),
    "HAS_OUTCOME": (("event", {"EVENT"}),),
    "BEFORE": (("earlier", {"EVENT"}), ("later", {"EVENT"})),
    "AFTER": (("later", {"EVENT"}), ("earlier", {"EVENT"})),
    "HAS_DEADLINE": (("task", {"TASK"}),),
    "OBSERVED_BY": (("observer", {"PARTICIPANT", "ENVIRONMENT"}), ("observed", ENTITY_TYPES)),
}


def _time(value: str | None) -> bool:
    if not isinstance(value, str) or not value: return False
    try: return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError: return False


def _issue(issues: list[ConformanceIssue], code: str, disposition: Disposition, record_id: str = "") -> None:
    issues.append(ConformanceIssue(code, disposition, record_id))


def _opaque_size(value: Any) -> int:
    return len(json.dumps(to_canonical_data(value), sort_keys=True, separators=(",", ":")).encode())


def validate_packet(packet: EvidencePacket | OpaqueEnvelope, bounds: ResourceBounds = ResourceBounds()) -> ConformanceReport:
    """Return a deterministic, non-policy structural conformance result."""
    issues: list[ConformanceIssue] = []
    if isinstance(packet, OpaqueEnvelope):
        if not packet.packet_id: _issue(issues, "MISSING_PACKET_ID", Disposition.REJECTED)
        elif _opaque_size(packet.payload) > bounds.max_opaque_bytes: _issue(issues, "OPAQUE_PAYLOAD_LIMIT", Disposition.QUARANTINED, packet.packet_id)
        else: return ConformanceReport(Disposition.OPAQUE)
    elif not isinstance(packet, EvidencePacket):
        return ConformanceReport(Disposition.REJECTED, (ConformanceIssue("MALFORMED_PACKET", Disposition.REJECTED),))
    else:
        if not packet.packet_id: _issue(issues, "MISSING_PACKET_ID", Disposition.REJECTED)
        if len(packet.relations) > bounds.max_relations: _issue(issues, "RELATION_LIMIT", Disposition.QUARANTINED, packet.packet_id)
        entities = _index(packet.entities, "entity_id", issues, "ENTITY")
        relations = _index(packet.relations, "relation_id", issues, "RELATION")
        assertions = _index(packet.assertions, "assertion_id", issues, "ASSERTION")
        verifications = _index(packet.verifications, "verification_id", issues, "VERIFICATION")
        for e in packet.entities:
            if not e.entity_id or not _scope_ok(e.scope): _issue(issues, "INVALID_ENTITY_IDENTITY", Disposition.REJECTED, e.entity_id)
            elif e.entity_type not in ENTITY_TYPES: _issue(issues, "UNSUPPORTED_ENTITY_TYPE", Disposition.QUARANTINED, e.entity_id)
            if _opaque_size(e.opaque_metadata) > bounds.max_opaque_bytes: _issue(issues, "OPAQUE_METADATA_LIMIT", Disposition.QUARANTINED, e.entity_id)
        for r in packet.relations: _validate_relation(r, entities, issues, bounds)
        verified = {v.assertion_id for v in packet.verifications if v.result == "VERIFIED" and v.verifier_id in entities and v.method_ref and v.evidence_ref and _time(v.verified_at)}
        for v in packet.verifications:
            if v.assertion_id not in assertions or v.verifier_id not in entities: _issue(issues, "DANGLING_VERIFICATION_REFERENCE", Disposition.QUARANTINED, v.verification_id)
            if not v.method_ref or not v.evidence_ref or not _time(v.verified_at): _issue(issues, "INVALID_VERIFICATION", Disposition.QUARANTINED, v.verification_id)
        for a in packet.assertions:
            _validate_assertion(a, entities, relations, assertions, verified, issues, bounds)
        _validate_cycles(packet.assertions, issues, bounds)
    if any(i.disposition is Disposition.REJECTED for i in issues): result = Disposition.REJECTED
    elif any(i.disposition is Disposition.QUARANTINED for i in issues): result = Disposition.QUARANTINED
    else: result = Disposition.STRUCTURAL
    return ConformanceReport(result, tuple(issues))


def _index(records: Iterable[Any], name: str, issues: list[ConformanceIssue], kind: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for record in records:
        ident = getattr(record, name, None)
        if not isinstance(ident, str) or not ident:
            _issue(issues, "MISSING_%s_ID" % kind, Disposition.REJECTED); continue
        if ident in result:
            if canonical_json(result[ident]) == canonical_json(record): _issue(issues, "EXACT_REPLAY", Disposition.STRUCTURAL, ident)
            else: _issue(issues, "ID_COLLISION", Disposition.REJECTED, ident)
        else: result[ident] = record
    return result


def _scope_ok(scope: Any) -> bool:
    return isinstance(scope, Scope) and bool(scope.segments) and all(isinstance(s, ScopeSegment) and bool(s.scope_type) and bool(s.scope_id) for s in scope.segments)


def _validate_relation(r: Relation, entities: Mapping[str, Entity], issues: list[ConformanceIssue], bounds: ResourceBounds) -> None:
    if r.vocabulary_version != CONTRACT_VERSION or r.relation_type not in RELATION_SCHEMAS:
        _issue(issues, "UNSUPPORTED_RELATION_VOCABULARY", Disposition.QUARANTINED, r.relation_id); return
    schema = RELATION_SCHEMAS[r.relation_type]
    seen = set()
    if len(r.endpoints) != len(schema): _issue(issues, "ENDPOINT_CARDINALITY", Disposition.REJECTED, r.relation_id)
    for endpoint in r.endpoints:
        if endpoint.role in seen: _issue(issues, "DUPLICATE_ENDPOINT_ROLE", Disposition.REJECTED, r.relation_id)
        seen.add(endpoint.role)
    for role, allowed in schema:
        endpoint = next((e for e in r.endpoints if e.role == role), None)
        if endpoint is None: continue
        entity = entities.get(endpoint.entity_id)
        if entity is None: _issue(issues, "DANGLING_ENDPOINT", Disposition.QUARANTINED, r.relation_id)
        elif entity.entity_type not in allowed: _issue(issues, "ENDPOINT_TYPE_MISMATCH", Disposition.REJECTED, r.relation_id)
    for q in r.qualifiers:
        if q.kind not in QUALIFIER_VOCABULARIES or q.value not in QUALIFIER_VOCABULARIES.get(q.kind, frozenset()): _issue(issues, "UNSUPPORTED_QUALIFIER_VOCABULARY", Disposition.QUARANTINED, r.relation_id)
        if r.relation_type == "HAS_DEADLINE" and q.kind == "CONTEXT": pass
    if r.relation_type == "HAS_STATE" and not any(q.kind == "STATE" for q in r.qualifiers): _issue(issues, "MISSING_STATE", Disposition.QUARANTINED, r.relation_id)
    if r.relation_type == "HAS_OUTCOME" and not any(q.kind == "OUTCOME" for q in r.qualifiers): _issue(issues, "MISSING_OUTCOME", Disposition.QUARANTINED, r.relation_id)
    if r.relation_type == "HAS_DEADLINE":
        deadline = next((q.value for q in r.qualifiers if q.kind == "CONTEXT"), None)
        if not _time(deadline): _issue(issues, "INVALID_DEADLINE", Disposition.QUARANTINED, r.relation_id)
    if _opaque_size(r.opaque_extensions) > bounds.max_opaque_bytes: _issue(issues, "OPAQUE_EXTENSION_LIMIT", Disposition.QUARANTINED, r.relation_id)


def _validate_assertion(a: Assertion, entities: Mapping[str, Entity], relations: Mapping[str, Relation], assertions: Mapping[str, Assertion], verified: set[str], issues: list[ConformanceIssue], bounds: ResourceBounds) -> None:
    if not a.assertion_id or a.assertor_id not in entities or entities.get(a.assertor_id).entity_type != "PARTICIPANT": _issue(issues, "INVALID_ASSERTOR", Disposition.REJECTED, a.assertion_id)
    if not a.source_instance_id or not _scope_ok(a.scope): _issue(issues, "INVALID_ASSERTION_IDENTITY", Disposition.REJECTED, a.assertion_id)
    if a.origin_kind not in ORIGIN_KINDS: _issue(issues, "UNSUPPORTED_ORIGIN", Disposition.QUARANTINED, a.assertion_id)
    if not _time(a.assertion_time) or not _time(a.availability_time): _issue(issues, "MISSING_OR_INVALID_AVAILABILITY", Disposition.QUARANTINED, a.assertion_id)
    if a.availability_phase not in PHASES: _issue(issues, "INVALID_PHASE", Disposition.QUARANTINED, a.assertion_id)
    if a.verification_status not in VERIFICATION_STATUSES: _issue(issues, "INVALID_VERIFICATION_STATUS", Disposition.QUARANTINED, a.assertion_id)
    if a.verification_status == "VERIFIED" and a.assertion_id not in verified: _issue(issues, "VERIFIED_WITHOUT_VALID_VERIFIER", Disposition.QUARANTINED, a.assertion_id)
    for relation_id in a.relation_ids:
        if relation_id not in relations: _issue(issues, "DANGLING_RELATION_REFERENCE", Disposition.QUARANTINED, a.assertion_id)
    if a.origin_kind == "DERIVED":
        if a.lineage is None or not a.lineage.parent_assertion_ids or not a.lineage.rule_id or not a.lineage.rule_version or not _time(a.lineage.derived_at): _issue(issues, "INCOMPLETE_DERIVATION", Disposition.QUARANTINED, a.assertion_id)
        elif any(parent not in assertions for parent in a.lineage.parent_assertion_ids): _issue(issues, "DANGLING_DERIVATION_PARENT", Disposition.QUARANTINED, a.assertion_id)
    elif a.lineage is not None: _issue(issues, "LINEAGE_ON_NON_DERIVED_ASSERTION", Disposition.QUARANTINED, a.assertion_id)
    if _opaque_size(a.opaque_metadata) > bounds.max_opaque_bytes: _issue(issues, "OPAQUE_METADATA_LIMIT", Disposition.QUARANTINED, a.assertion_id)


def _validate_cycles(assertions: Iterable[Assertion], issues: list[ConformanceIssue], bounds: ResourceBounds) -> None:
    graph = {a.assertion_id: a.lineage.parent_assertion_ids if a.lineage else () for a in assertions}
    def visit(node: str, stack: tuple[str, ...]) -> None:
        if len(stack) > bounds.max_lineage_depth: _issue(issues, "LINEAGE_DEPTH_LIMIT", Disposition.QUARANTINED, node); return
        if node in stack: _issue(issues, "DERIVATION_CYCLE", Disposition.REJECTED, node); return
        for parent in graph.get(node, ()): visit(parent, stack + (node,))
    for node in sorted(graph): visit(node, ())


def temporally_eligible(assertion: Assertion, boundary_time: str, boundary_phase: str, scope: Scope) -> bool:
    """Pure caller-supplied historical selection; it grants no admission or authority."""
    if not _time(boundary_time) or boundary_phase not in PHASES or not _scope_ok(scope): return False
    if not _time(assertion.availability_time) or assertion.availability_phase not in PHASES or assertion.scope != scope: return False
    return (datetime.fromisoformat(assertion.availability_time.replace("Z", "+00:00")), PHASES.index(assertion.availability_phase)) <= (datetime.fromisoformat(boundary_time.replace("Z", "+00:00")), PHASES.index(boundary_phase))


def to_canonical_data(value: Any) -> Any:
    if isinstance(value, Enum): return value.value
    if isinstance(value, FrozenMap): return {k: to_canonical_data(v) for k, v in value}
    if is_dataclass(value): return {"_type": type(value).__name__, **{f.name: to_canonical_data(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, tuple): return [to_canonical_data(v) for v in value]
    if isinstance(value, Mapping): return {str(k): to_canonical_data(v) for k, v in sorted(value.items())}
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(to_canonical_data(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


_TYPES = {c.__name__: c for c in (ScopeSegment, Scope, Entity, Endpoint, Qualifier, Relation, Lineage, Assertion, Verification, ResourceBounds, EvidencePacket, OpaqueEnvelope)}
def from_canonical_json(text: str) -> Any:
    def rebuild(value: Any) -> Any:
        if isinstance(value, list): return tuple(rebuild(v) for v in value)
        if not isinstance(value, dict): return value
        type_name = value.get("_type")
        if type_name:
            cls = _TYPES[type_name]; return cls(**{k: rebuild(v) for k, v in value.items() if k != "_type"})
        return FrozenMap({k: rebuild(v) for k, v in value.items()})
    return rebuild(json.loads(text))

"""Neutral, source-authorized runtime action value and availability evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

SCHEMA_VERSION = "ETHOS_RUNTIME_ACTION_CONTEXT_PRODUCER_V1"
MEASURE_BENEFIT = "MEASURE_BENEFIT"
MEASURE_EFFORT = "MEASURE_EFFORT"
ASSERT_AVAILABILITY = "ASSERT_AVAILABILITY"
ASSERT_BLOCKER = "ASSERT_BLOCKER"
ASSERT_PREREQUISITE = "ASSERT_PREREQUISITE"
CAPABILITIES = frozenset({MEASURE_BENEFIT, MEASURE_EFFORT, ASSERT_AVAILABILITY, ASSERT_BLOCKER, ASSERT_PREREQUISITE})
TRUSTED_SOURCE_TYPES = frozenset({"USER_ASSERTION", "SYSTEM_ASSERTION", "AUTHORITY_ADAPTER", "VERIFIED_EXTERNAL_EVIDENCE"})
AVAILABILITY_STATES = frozenset({"AVAILABLE", "UNAVAILABLE", "UNKNOWN"})
BLOCKER_STATES = frozenset({"ACTIVE", "CLEARED", "UNKNOWN"})
RELATION_STATES = frozenset({"ACTIVE", "INACTIVE", "UNKNOWN"})
PHASES = frozenset({"EXPECTED", "OBSERVED"})
DEFAULT_EVIDENCE_DIRECTORY = Path(__file__).with_name("evidence")
DEFAULT_AUTHORITY_PATH = DEFAULT_EVIDENCE_DIRECTORY / "runtime_measurement_authority.jsonl"
DEFAULT_VALUE_PATH = DEFAULT_EVIDENCE_DIRECTORY / "runtime_action_values.jsonl"
DEFAULT_AVAILABILITY_PATH = DEFAULT_EVIDENCE_DIRECTORY / "runtime_action_availability.jsonl"
DEFAULT_BLOCKER_PATH = DEFAULT_EVIDENCE_DIRECTORY / "runtime_action_blockers.jsonl"
DEFAULT_PREREQUISITE_PATH = DEFAULT_EVIDENCE_DIRECTORY / "runtime_action_prerequisites.jsonl"


@dataclass(frozen=True)
class RuntimeContextSource:
    source_id: str
    source_type: str
    source_instance_id: str
    evidence_reference: str | None = None


@dataclass(frozen=True)
class RuntimeMeasurementBasis:
    basis_id: str
    dimension: str
    representation: str
    unit_or_scale: str
    ordinal_order: tuple[str, ...] = ()
    source_version: str = "v1"


@dataclass(frozen=True)
class RuntimeMeasurementAuthorityGrant:
    schema_version: str
    grant_id: str
    issuer_id: str
    authorized_producer_id: str
    capability: str
    basis_id: str | None
    scope_id: str
    valid_from: str
    valid_until: str | None
    timestamp: str
    source: RuntimeContextSource
    sequence_id: int

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class RuntimeActionValueClaim:
    schema_version: str
    claim_id: str
    dimension: str
    objective_id: str
    action_id: str
    actor_id: str
    scope_id: str
    value: float | str | None
    basis_id: str
    phase: str
    valid_from: str
    valid_until: str | None
    producer_id: str
    authority_grant_id: str | None
    timestamp: str
    source: RuntimeContextSource
    sequence_id: int

    def to_dict(self): return asdict(self)


RuntimeActionBenefitClaim = RuntimeActionValueClaim
RuntimeActionEffortClaim = RuntimeActionValueClaim


@dataclass(frozen=True)
class RuntimeActionAvailabilityClaim:
    schema_version: str
    claim_id: str
    objective_id: str
    action_id: str
    actor_id: str
    scope_id: str
    state: str
    valid_from: str
    valid_until: str | None
    producer_id: str
    authority_grant_id: str | None
    timestamp: str
    source: RuntimeContextSource
    sequence_id: int

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class RuntimeActionBlockerClaim:
    schema_version: str
    blocker_id: str
    objective_id: str
    action_id: str
    scope_id: str
    state: str
    blocker_type: str
    valid_from: str
    valid_until: str | None
    producer_id: str
    authority_grant_id: str | None
    timestamp: str
    source: RuntimeContextSource
    sequence_id: int

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class RuntimeActionPrerequisiteClaim:
    schema_version: str
    relation_id: str
    objective_id: str
    prerequisite_action_id: str
    dependent_action_id: str
    scope_id: str
    state: str
    valid_from: str
    valid_until: str | None
    producer_id: str
    authority_grant_id: str | None
    timestamp: str
    source: RuntimeContextSource
    sequence_id: int

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class ActionContextReport:
    grants: tuple[RuntimeMeasurementAuthorityGrant, ...]
    values: tuple[RuntimeActionValueClaim, ...]
    availability: tuple[RuntimeActionAvailabilityClaim, ...]
    blockers: tuple[RuntimeActionBlockerClaim, ...]
    prerequisites: tuple[RuntimeActionPrerequisiteClaim, ...]
    issues: tuple[str, ...]


def validate_basis(basis: RuntimeMeasurementBasis) -> tuple[str, ...]:
    issues=[]
    if not basis.basis_id or basis.dimension not in {"BENEFIT", "EFFORT"} or basis.representation not in {"NUMERIC", "ORDINAL"} or not basis.unit_or_scale: issues.append("MALFORMED")
    if basis.representation == "ORDINAL" and (not basis.ordinal_order or len(set(basis.ordinal_order)) != len(basis.ordinal_order)): issues.append("INVALID_ORDINAL_BASIS")
    if basis.representation == "NUMERIC" and basis.ordinal_order: issues.append("INVALID_NUMERIC_BASIS")
    return tuple(sorted(set(issues)))


def validate_grant(item: RuntimeMeasurementAuthorityGrant) -> tuple[str, ...]:
    issues = _common(item, item.grant_id, item.scope_id, item.timestamp)
    if not all((item.issuer_id, item.authorized_producer_id, item.valid_from)): issues.append("MALFORMED")
    if item.capability not in CAPABILITIES: issues.append("INVALID_CAPABILITY")
    if item.issuer_id == item.authorized_producer_id: issues.append("SELF_GRANTED_AUTHORITY")
    if item.source.source_id != item.issuer_id: issues.append("GRANT_SOURCE_MISMATCH")
    if item.source.source_type not in TRUSTED_SOURCE_TYPES: issues.append("UNTRUSTED_GRANT_SOURCE")
    if not _interval(item.valid_from, item.valid_until): issues.append("INVALID_INTERVAL")
    return tuple(sorted(set(issues)))


def validate_value(item: RuntimeActionValueClaim, bases: tuple[RuntimeMeasurementBasis, ...] = ()) -> tuple[str, ...]:
    issues = _common(item, item.claim_id, item.scope_id, item.timestamp)
    if not all((item.dimension, item.objective_id, item.action_id, item.actor_id, item.basis_id, item.phase, item.valid_from, item.producer_id)): issues.append("MALFORMED")
    if item.dimension not in {"BENEFIT", "EFFORT"} or item.phase not in PHASES: issues.append("MALFORMED")
    if not _interval(item.valid_from, item.valid_until): issues.append("INVALID_INTERVAL")
    basis = next((basis for basis in bases if basis.basis_id == item.basis_id), None)
    if bases and (basis is None or validate_basis(basis) or basis.dimension != item.dimension): issues.append("BASIS_MISMATCH")
    return tuple(sorted(set(issues)))


def validate_availability(item: RuntimeActionAvailabilityClaim) -> tuple[str, ...]:
    issues = _common(item, item.claim_id, item.scope_id, item.timestamp)
    if not all((item.objective_id, item.action_id, item.actor_id, item.producer_id, item.valid_from)) or item.state not in AVAILABILITY_STATES: issues.append("MALFORMED")
    if not _interval(item.valid_from, item.valid_until): issues.append("INVALID_INTERVAL")
    return tuple(sorted(set(issues)))


def validate_blocker(item: RuntimeActionBlockerClaim) -> tuple[str, ...]:
    issues = _common(item, item.blocker_id, item.scope_id, item.timestamp)
    if not all((item.objective_id, item.action_id, item.blocker_type, item.producer_id, item.valid_from)) or item.state not in BLOCKER_STATES: issues.append("MALFORMED")
    if not _interval(item.valid_from, item.valid_until): issues.append("INVALID_INTERVAL")
    return tuple(sorted(set(issues)))


def validate_prerequisite(item: RuntimeActionPrerequisiteClaim) -> tuple[str, ...]:
    issues = _common(item, item.relation_id, item.scope_id, item.timestamp)
    if not all((item.objective_id, item.prerequisite_action_id, item.dependent_action_id, item.producer_id, item.valid_from)) or item.state not in RELATION_STATES or item.prerequisite_action_id == item.dependent_action_id: issues.append("INVALID_PREREQUISITE")
    if not _interval(item.valid_from, item.valid_until): issues.append("INVALID_INTERVAL")
    return tuple(sorted(set(issues)))


def authority_status(grant, *, producer_id, capability, basis_id, scope_id, at):
    if grant is None: return "UNKNOWN_AUTHORITY"
    if validate_grant(grant): return "MALFORMED"
    if grant.authorized_producer_id != producer_id or grant.capability != capability: return "UNAUTHORIZED"
    if grant.basis_id != basis_id: return "BASIS_MISMATCH"
    if grant.scope_id != scope_id: return "SCOPE_MISMATCH"
    try:
        if _time(at) < _time(grant.valid_from) or (grant.valid_until and _time(at) > _time(grant.valid_until)): return "EXPIRED_AUTHORITY"
    except ValueError: return "MALFORMED"
    return "VALID"


def claim_authority_status(item, grants, *, capability, basis_id=None, at=None):
    matches=[grant for grant in grants if grant.grant_id == item.authority_grant_id]
    if not matches: return "UNKNOWN_AUTHORITY"
    if len(matches) != 1: return "CONFLICT"
    return authority_status(matches[0], producer_id=item.producer_id, capability=capability, basis_id=basis_id, scope_id=item.scope_id, at=at or item.timestamp)


def usable_values(values, grants, bases, *, dimension, objective_id, action_id, actor_id, scope_id, at):
    matching=[]
    for item in values:
        if (item.dimension, item.objective_id, item.action_id, item.actor_id, item.scope_id) != (dimension, objective_id, action_id, actor_id, scope_id): continue
        if item.phase != "EXPECTED" or not _at(item.valid_from, item.valid_until, at): continue
        if validate_value(item, bases): continue
        if claim_authority_status(item, grants, capability=MEASURE_BENEFIT if dimension == "BENEFIT" else MEASURE_EFFORT, basis_id=item.basis_id, at=at) == "VALID": matching.append(item)
    if not matching: return (), "UNKNOWN"
    if len({(item.basis_id, item.value) for item in matching}) != 1: return tuple(matching), "CONFLICT"
    return tuple(matching), "VALID"


def availability_at(claims, grants, *, objective_id, action_id, actor_id, scope_id, at):
    matching=[item for item in claims if (item.objective_id,item.action_id,item.actor_id,item.scope_id)==(objective_id,action_id,actor_id,scope_id) and _at(item.valid_from,item.valid_until,at) and not validate_availability(item) and claim_authority_status(item,grants,capability=ASSERT_AVAILABILITY,at=at)=="VALID"]
    if not matching: return "UNKNOWN"
    states={item.state for item in matching}
    return next(iter(states)) if len(states)==1 else "CONFLICT"


def blocker_at(claims, grants, *, objective_id, action_id, scope_id, at):
    matching=[item for item in claims if (item.objective_id,item.action_id,item.scope_id)==(objective_id,action_id,scope_id) and _at(item.valid_from,item.valid_until,at) and not validate_blocker(item) and claim_authority_status(item,grants,capability=ASSERT_BLOCKER,at=at)=="VALID"]
    if not matching: return "NONE"
    states={item.state for item in matching}
    return next(iter(states)) if len(states)==1 else "CONFLICT"


def prerequisite_at(claims, grants, *, objective_id, prerequisite_action_id, dependent_action_id, scope_id, at):
    matching=[item for item in claims if (item.objective_id,item.prerequisite_action_id,item.dependent_action_id,item.scope_id)==(objective_id,prerequisite_action_id,dependent_action_id,scope_id) and _at(item.valid_from,item.valid_until,at) and not validate_prerequisite(item) and claim_authority_status(item,grants,capability=ASSERT_PREREQUISITE,at=at)=="VALID"]
    if not matching: return "NONE"
    states={item.state for item in matching}
    return next(iter(states)) if len(states)==1 else "CONFLICT"


class RuntimeActionContextProducer:
    def __init__(self, authority_path=DEFAULT_AUTHORITY_PATH, value_path=DEFAULT_VALUE_PATH, availability_path=DEFAULT_AVAILABILITY_PATH, blocker_path=DEFAULT_BLOCKER_PATH, prerequisite_path=DEFAULT_PREREQUISITE_PATH, source_instance_id=None):
        self.paths={"authority":Path(authority_path),"value":Path(value_path),"availability":Path(availability_path),"blocker":Path(blocker_path),"prerequisite":Path(prerequisite_path)}; self.source_instance_id=source_instance_id or f"context-runtime-{uuid4()}"; self.seq={key:0 for key in self.paths}
    def grant(self, *, issuer_id, authorized_producer_id, capability, basis_id, scope_id, source_id, source_type, valid_from, valid_until=None, grant_id=None, timestamp=None, evidence_reference=None):
        item=RuntimeMeasurementAuthorityGrant(SCHEMA_VERSION,grant_id or f"grant-{uuid4()}",issuer_id,authorized_producer_id,capability,basis_id,scope_id,valid_from,valid_until,timestamp or _now(),self._source(source_id,source_type,evidence_reference),self._next("authority")); self._write("authority",item,validate_grant); return item
    def value(self, *, dimension, objective_id, action_id, actor_id, scope_id, value, basis_id, phase, producer_id, authority_grant_id, source_id, source_type, valid_from, valid_until=None, claim_id=None, timestamp=None, evidence_reference=None):
        item=RuntimeActionValueClaim(SCHEMA_VERSION,claim_id or f"value-{uuid4()}",dimension,objective_id,action_id,actor_id,scope_id,value,basis_id,phase,valid_from,valid_until,producer_id,authority_grant_id,timestamp or _now(),self._source(source_id,source_type,evidence_reference),self._next("value")); self._write("value",item,validate_value); return item
    def availability(self, *, objective_id, action_id, actor_id, scope_id, state, producer_id, authority_grant_id, source_id, source_type, valid_from, valid_until=None, claim_id=None, timestamp=None, evidence_reference=None):
        item=RuntimeActionAvailabilityClaim(SCHEMA_VERSION,claim_id or f"availability-{uuid4()}",objective_id,action_id,actor_id,scope_id,state,valid_from,valid_until,producer_id,authority_grant_id,timestamp or _now(),self._source(source_id,source_type,evidence_reference),self._next("availability")); self._write("availability",item,validate_availability); return item
    def blocker(self, *, objective_id, action_id, scope_id, state, blocker_type, producer_id, authority_grant_id, source_id, source_type, valid_from, valid_until=None, blocker_id=None, timestamp=None, evidence_reference=None):
        item=RuntimeActionBlockerClaim(SCHEMA_VERSION,blocker_id or f"blocker-{uuid4()}",objective_id,action_id,scope_id,state,blocker_type,valid_from,valid_until,producer_id,authority_grant_id,timestamp or _now(),self._source(source_id,source_type,evidence_reference),self._next("blocker")); self._write("blocker",item,validate_blocker); return item
    def prerequisite(self, *, objective_id, prerequisite_action_id, dependent_action_id, scope_id, state, producer_id, authority_grant_id, source_id, source_type, valid_from, valid_until=None, relation_id=None, timestamp=None, evidence_reference=None):
        item=RuntimeActionPrerequisiteClaim(SCHEMA_VERSION,relation_id or f"prerequisite-{uuid4()}",objective_id,prerequisite_action_id,dependent_action_id,scope_id,state,valid_from,valid_until,producer_id,authority_grant_id,timestamp or _now(),self._source(source_id,source_type,evidence_reference),self._next("prerequisite")); self._write("prerequisite",item,validate_prerequisite); return item
    def _source(self,a,b,c): return RuntimeContextSource(a,b,self.source_instance_id,c)
    def _next(self,key): self.seq[key]+=1; return self.seq[key]
    def _write(self,key,item,validator):
        issues=validator(item)
        if issues: self.seq[key]-=1; raise ValueError(",".join(issues))
        self.paths[key].parent.mkdir(parents=True,exist_ok=True)
        with self.paths[key].open("a",encoding="utf-8") as handle: handle.write(json.dumps(item.to_dict(),sort_keys=True,separators=(",",":"))+"\n")


def load_action_context(authority_path, value_path, availability_path, blocker_path, prerequisite_path):
    grants,gi=_load(authority_path,RuntimeMeasurementAuthorityGrant,validate_grant,"authority","grant_id")
    values,vi=_load(value_path,RuntimeActionValueClaim,lambda x:validate_value(x),"value","claim_id")
    availability,ai=_load(availability_path,RuntimeActionAvailabilityClaim,validate_availability,"availability","claim_id")
    blockers,bi=_load(blocker_path,RuntimeActionBlockerClaim,validate_blocker,"blocker","blocker_id")
    prereq,pi=_load(prerequisite_path,RuntimeActionPrerequisiteClaim,validate_prerequisite,"prerequisite","relation_id")
    issues=list(gi+vi+ai+bi+pi)
    for item,cap,name in [(x,MEASURE_BENEFIT if x.dimension=="BENEFIT" else MEASURE_EFFORT,"value") for x in values]+[(x,ASSERT_AVAILABILITY,"availability") for x in availability]+[(x,ASSERT_BLOCKER,"blocker") for x in blockers]+[(x,ASSERT_PREREQUISITE,"prerequisite") for x in prereq]:
        basis_id=getattr(item,"basis_id",None)
        if claim_authority_status(item,grants,capability=cap,basis_id=basis_id,at=getattr(item,"timestamp")) != "VALID": issues.append(f"UNAUTHORIZED_{name.upper()}:{getattr(item,'claim_id',getattr(item,'blocker_id',getattr(item,'relation_id','')))}")
    return ActionContextReport(tuple(grants),tuple(values),tuple(availability),tuple(blockers),tuple(prereq),tuple(sorted(set(issues))))


def to_research_basis(basis):
    from ethos_action_value_research import MeasurementBasis
    return MeasurementBasis(basis.basis_id,basis.dimension,basis.representation,basis.unit_or_scale,basis.ordinal_order)


def to_research_authority(grant):
    from factual_context_research import Source, VerificationState
    from ethos_required_work_research import Attribution
    from ethos_action_value_research import MeasurementAuthorityClaim
    source=Source(grant.source.source_type) if grant.source.source_type in Source._value2member_map_ else Source.UNKNOWN_SOURCE
    attr=Attribution(source,grant.source.source_instance_id,grant.scope_id,grant.timestamp,VerificationState.ASSERTED,f"runtime-source:{grant.source.source_id};reference:{grant.source.evidence_reference or ''}")
    return MeasurementAuthorityClaim(grant.grant_id,grant.authorized_producer_id,grant.basis_id or "", "CONFIRMED" if not validate_grant(grant) else "UNKNOWN",attr)


def to_research_value(item):
    from factual_context_research import Source, VerificationState
    from ethos_required_work_research import Attribution
    from ethos_action_value_research import ActionBenefitClaim, ActionEffortClaim
    source=Source(item.source.source_type) if item.source.source_type in Source._value2member_map_ else Source.UNKNOWN_SOURCE
    attr=Attribution(source,item.source.source_instance_id,item.scope_id,item.timestamp,VerificationState.ASSERTED,f"runtime-source:{item.source.source_id};reference:{item.source.evidence_reference or ''}")
    cls=ActionBenefitClaim if item.dimension=="BENEFIT" else ActionEffortClaim
    return cls(item.claim_id,item.objective_id,item.action_id,item.actor_id,item.scope_id,item.value,item.basis_id,item.phase,item.valid_from,item.valid_until,item.producer_id,attr,item.authority_grant_id)


def apply_context_to_decision_entry(entry, report, *, bases):
    """Return an existing research entry with only validated availability/context claims added."""
    from ethos_action_decision_research import ActionDecisionRecord, ActionCandidate, ContextClaim, SourceAttribution
    candidates=[]; claims=list(entry.decision.claims)
    for candidate in entry.decision.candidates:
        state=availability_at(report.availability,report.grants,objective_id=entry.decision.objective_id,action_id=candidate.action_id,actor_id=entry.actor_id,scope_id=entry.scope_id,at=entry.decided_at)
        available=state if state in {"AVAILABLE","UNAVAILABLE","UNKNOWN"} else "UNKNOWN"
        candidates.append(replace(candidate,available=available))
        block=blocker_at(report.blockers,report.grants,objective_id=entry.decision.objective_id,action_id=candidate.action_id,scope_id=entry.scope_id,at=entry.decided_at)
        if block=="ACTIVE": claims.append(ContextClaim(f"runtime-blocker-{candidate.action_id}",candidate.action_id,"VALID_BLOCKER","PRESENT",SourceAttribution("runtime-context",entry.source_instance_id,entry.scope_id,entry.decided_at)))
    selected=entry.decision.selected_action_id
    required=next((candidate.action_id for candidate in candidates if candidate.action_id != selected),None)
    if selected and required and prerequisite_at(report.prerequisites,report.grants,objective_id=entry.decision.objective_id,prerequisite_action_id=selected,dependent_action_id=required,scope_id=entry.scope_id,at=entry.decided_at)=="ACTIVE": claims.append(ContextClaim("runtime-prerequisite",selected,"PREREQUISITE","PRESENT",SourceAttribution("runtime-context",entry.source_instance_id,entry.scope_id,entry.decided_at)))
    decision=replace(entry.decision,candidates=tuple(candidates),claims=tuple(claims))
    return replace(entry,decision=decision)


def _load(path,cls,validator,stream,identity):
    values=[]; issues=[]
    try: lines=Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError: return [],[]
    except OSError as error: return [],[f"READ_ERROR:{stream}:{error}"]
    for number,line in enumerate(lines,1):
        try:
            raw=json.loads(line); raw["source"]=RuntimeContextSource(**raw["source"]); item=cls(**raw)
        except Exception: issues.append(f"MALFORMED_ENTRY:{stream}:{number}"); continue
        issues.extend(f"{issue}:{stream}:{number}" for issue in validator(item)); values.append(item)
    ids=[getattr(item,identity) for item in values]
    if len(ids)!=len(set(ids)): issues.append(f"DUPLICATE_ID:{stream}")
    for instance in {item.source.source_instance_id for item in values}:
        stream_values=[item for item in values if item.source.source_instance_id==instance]
        if [item.sequence_id for item in stream_values]!=list(range(1,len(stream_values)+1)): issues.append(f"INVALID_SEQUENCE_ORDER:{stream}:{instance}")
    return values,issues


def _common(item,identity,scope,timestamp):
    issues=[]
    if item.schema_version!=SCHEMA_VERSION or not identity or not scope or item.sequence_id<1: issues.append("MALFORMED")
    if not all((item.source.source_id,item.source.source_type,item.source.source_instance_id)): issues.append("INVALID_SOURCE")
    try: _time(timestamp)
    except ValueError: issues.append("INVALID_TIMESTAMP")
    return issues
def _time(v): return datetime.fromisoformat(v.replace("Z","+00:00"))
def _interval(a,b):
    try: return b is None or _time(a)<=_time(b)
    except ValueError: return False
def _at(a,b,at):
    try: return _time(a)<=_time(at) and (b is None or _time(at)<=_time(b))
    except ValueError: return False
def _now(): return datetime.now(timezone.utc).isoformat()

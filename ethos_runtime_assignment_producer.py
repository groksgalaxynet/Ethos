"""Neutral, append-only runtime authority and required-work assignment evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

SCHEMA_VERSION = "ETHOS_RUNTIME_ASSIGNMENT_PRODUCER_V1"
ASSIGN_REQUIRED_WORK = "ASSIGN_REQUIRED_WORK"
COMPLETE_REQUIRED_WORK = "COMPLETE_REQUIRED_WORK"
CANCEL_REQUIRED_WORK = "CANCEL_REQUIRED_WORK"
SUPERSEDE_REQUIRED_WORK = "SUPERSEDE_REQUIRED_WORK"
DELEGATE_REQUIRED_WORK = "DELEGATE_REQUIRED_WORK"
ASSERT_REQUIRED_WORK_BLOCKED = "ASSERT_REQUIRED_WORK_BLOCKED"
EXPIRE_REQUIRED_WORK = "EXPIRE_REQUIRED_WORK"
AUTHORITY_TYPES = frozenset({
    ASSIGN_REQUIRED_WORK, COMPLETE_REQUIRED_WORK, CANCEL_REQUIRED_WORK,
    SUPERSEDE_REQUIRED_WORK, DELEGATE_REQUIRED_WORK, ASSERT_REQUIRED_WORK_BLOCKED,
    EXPIRE_REQUIRED_WORK,
})
TRUSTED_GRANT_SOURCE_TYPES = frozenset({
    "USER_ASSERTION", "SYSTEM_ASSERTION", "AUTHORITY_ADAPTER", "VERIFIED_EXTERNAL_EVIDENCE",
})
REQUIREMENTS = frozenset({"REQUIRED", "OPTIONAL", "UNKNOWN"})
LIFECYCLE_STATES = frozenset({"ACTIVE", "COMPLETED", "CANCELLED", "SUPERSEDED", "BLOCKED", "DELEGATED", "EXPIRED"})
LIFECYCLE_AUTHORITY = {
    "ACTIVE": ASSIGN_REQUIRED_WORK,
    "COMPLETED": COMPLETE_REQUIRED_WORK,
    "CANCELLED": CANCEL_REQUIRED_WORK,
    "SUPERSEDED": SUPERSEDE_REQUIRED_WORK,
    "DELEGATED": DELEGATE_REQUIRED_WORK,
    "BLOCKED": ASSERT_REQUIRED_WORK_BLOCKED,
    "EXPIRED": EXPIRE_REQUIRED_WORK,
}
DEFAULT_EVIDENCE_DIRECTORY = Path(__file__).with_name("evidence")
DEFAULT_AUTHORITY_LOG_PATH = DEFAULT_EVIDENCE_DIRECTORY / "runtime_authority.jsonl"
DEFAULT_ASSIGNMENT_LOG_PATH = DEFAULT_EVIDENCE_DIRECTORY / "runtime_assignments.jsonl"
DEFAULT_LIFECYCLE_LOG_PATH = DEFAULT_EVIDENCE_DIRECTORY / "runtime_assignment_lifecycle.jsonl"


@dataclass(frozen=True)
class RuntimeSourceAttribution:
    source_id: str
    source_type: str
    source_instance_id: str
    evidence_reference: str | None = None


@dataclass(frozen=True)
class RuntimeAuthorityGrant:
    schema_version: str
    grant_id: str
    issuer_id: str
    authorized_principal_id: str
    authority_type: str
    scope_id: str
    valid_from: str
    valid_until: str | None
    timestamp: str
    source: RuntimeSourceAttribution
    sequence_id: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeWorkAssignment:
    schema_version: str
    assignment_id: str
    objective_id: str
    work_id: str
    assigned_actor_id: str
    issuer_id: str
    scope_id: str
    requirement: str
    assignment_at: str
    authority_grant_id: str | None
    source: RuntimeSourceAttribution
    sequence_id: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeAssignmentLifecycleEvent:
    schema_version: str
    event_id: str
    assignment_id: str
    state: str
    event_at: str
    issuer_id: str
    authority_grant_id: str | None
    source: RuntimeSourceAttribution
    sequence_id: int
    delegate_actor_id: str | None = None
    replacement_assignment_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AssignmentEvidenceReport:
    grants: tuple[RuntimeAuthorityGrant, ...]
    assignments: tuple[RuntimeWorkAssignment, ...]
    lifecycle: tuple[RuntimeAssignmentLifecycleEvent, ...]
    issues: tuple[str, ...]


def validate_grant(grant: RuntimeAuthorityGrant) -> tuple[str, ...]:
    issues = _common_issues(grant, grant.grant_id, grant.scope_id, grant.timestamp)
    if not all((grant.issuer_id, grant.authorized_principal_id, grant.valid_from)):
        issues.append("MISSING_GRANT_IDENTITY")
    if grant.authority_type not in AUTHORITY_TYPES:
        issues.append("INVALID_AUTHORITY_TYPE")
    if grant.issuer_id == grant.authorized_principal_id:
        issues.append("SELF_GRANTED_AUTHORITY")
    if grant.source.source_id != grant.issuer_id:
        issues.append("GRANT_SOURCE_MISMATCH")
    if grant.source.source_type not in TRUSTED_GRANT_SOURCE_TYPES:
        issues.append("UNTRUSTED_GRANT_SOURCE")
    if not _valid_interval(grant.valid_from, grant.valid_until):
        issues.append("INVALID_AUTHORITY_INTERVAL")
    return tuple(sorted(set(issues)))


def validate_assignment(assignment: RuntimeWorkAssignment) -> tuple[str, ...]:
    issues = _common_issues(assignment, assignment.assignment_id, assignment.scope_id, assignment.assignment_at)
    if not all((assignment.objective_id, assignment.work_id, assignment.assigned_actor_id, assignment.issuer_id)):
        issues.append("MISSING_ASSIGNMENT_IDENTITY")
    if assignment.requirement not in REQUIREMENTS:
        issues.append("INVALID_REQUIREMENT")
    return tuple(sorted(set(issues)))


def validate_lifecycle(event: RuntimeAssignmentLifecycleEvent) -> tuple[str, ...]:
    issues = _common_issues(event, event.event_id, event.source.source_id and event.source.source_instance_id and "scope", event.event_at)
    if not all((event.assignment_id, event.issuer_id)):
        issues.append("MISSING_LIFECYCLE_IDENTITY")
    if event.state not in LIFECYCLE_STATES:
        issues.append("INVALID_LIFECYCLE")
    if event.state == "DELEGATED" and not event.delegate_actor_id:
        issues.append("MISSING_DELEGATE")
    if event.state != "DELEGATED" and event.delegate_actor_id is not None:
        issues.append("UNEXPECTED_DELEGATE")
    if event.state == "SUPERSEDED" and not event.replacement_assignment_id:
        issues.append("MISSING_REPLACEMENT")
    if event.state != "SUPERSEDED" and event.replacement_assignment_id is not None:
        issues.append("UNEXPECTED_REPLACEMENT")
    return tuple(sorted(set(issues)))


def authority_status(grant: RuntimeAuthorityGrant | None, *, principal_id: str, authority_type: str, scope_id: str, at: str) -> str:
    if grant is None:
        return "UNKNOWN_AUTHORITY"
    if validate_grant(grant):
        return "MALFORMED"
    if grant.authorized_principal_id != principal_id:
        return "UNAUTHORIZED"
    if grant.authority_type != authority_type:
        return "UNAUTHORIZED"
    if grant.scope_id != scope_id:
        return "SCOPE_MISMATCH"
    try:
        when = _time(at)
        if when < _time(grant.valid_from) or (grant.valid_until is not None and when > _time(grant.valid_until)):
            return "EXPIRED_AUTHORITY"
    except ValueError:
        return "MALFORMED"
    return "VALID"


def assignment_authority_status(assignment: RuntimeWorkAssignment, grants: tuple[RuntimeAuthorityGrant, ...]) -> str:
    if validate_assignment(assignment):
        return "MALFORMED"
    matches = [grant for grant in grants if grant.grant_id == assignment.authority_grant_id]
    if not matches:
        return "UNKNOWN_AUTHORITY"
    if len(matches) != 1:
        return "CONFLICT"
    return authority_status(matches[0], principal_id=assignment.issuer_id, authority_type=ASSIGN_REQUIRED_WORK, scope_id=assignment.scope_id, at=assignment.assignment_at)


def lifecycle_authority_status(event: RuntimeAssignmentLifecycleEvent, assignment: RuntimeWorkAssignment | None, grants: tuple[RuntimeAuthorityGrant, ...]) -> str:
    if validate_lifecycle(event):
        return "MALFORMED"
    if assignment is None:
        return "UNKNOWN_ASSIGNMENT"
    matches = [grant for grant in grants if grant.grant_id == event.authority_grant_id]
    if not matches:
        return "UNKNOWN_AUTHORITY"
    if len(matches) != 1:
        return "CONFLICT"
    return authority_status(matches[0], principal_id=event.issuer_id, authority_type=LIFECYCLE_AUTHORITY[event.state], scope_id=assignment.scope_id, at=event.event_at)


def derive_assignment_state(assignment: RuntimeWorkAssignment, grants: tuple[RuntimeAuthorityGrant, ...], lifecycle: tuple[RuntimeAssignmentLifecycleEvent, ...], *, actor_id: str, scope_id: str, at: str) -> str:
    """Derive factual state at ``at`` without changing historical records."""
    status = assignment_authority_status(assignment, grants)
    if status != "VALID":
        return status
    if assignment.assigned_actor_id != actor_id:
        return "ACTOR_MISMATCH"
    if assignment.scope_id != scope_id:
        return "SCOPE_MISMATCH"
    if assignment.requirement == "UNKNOWN":
        return "UNKNOWN_REQUIREMENT"
    try:
        decision_time = _time(at)
    except ValueError:
        return "MALFORMED"
    if decision_time < _time(assignment.assignment_at):
        return "NOT_YET_ASSIGNED"
    relevant = [event for event in lifecycle if event.assignment_id == assignment.assignment_id and _before_or_equal(event.event_at, at)]
    if any(_time(event.event_at) < _time(assignment.assignment_at) for event in relevant):
        return "INVALID_LIFECYCLE_EVIDENCE"
    if any(lifecycle_authority_status(event, assignment, grants) != "VALID" for event in relevant):
        return "INVALID_LIFECYCLE_EVIDENCE"
    try:
        relevant.sort(key=lambda event: (_time(event.event_at), event.sequence_id, event.event_id))
    except ValueError:
        return "MALFORMED"
    if assignment.authority_grant_id:
        grant = next((value for value in grants if value.grant_id == assignment.authority_grant_id), None)
        if grant and grant.valid_until and decision_time > _time(grant.valid_until):
            return "EXPIRED"
    terminal = {"COMPLETED", "CANCELLED", "SUPERSEDED", "BLOCKED", "DELEGATED", "EXPIRED"}
    states = {event.state for event in relevant if event.state in terminal}
    if len(states) > 1:
        return "CONFLICT"
    if states:
        state = next(iter(states))
        if state == "DELEGATED":
            event = next(event for event in relevant if event.state == state)
            return "DELEGATED_TO_SELF" if event.delegate_actor_id == actor_id else "DELEGATED_AWAY"
        return state
    return "REQUIRED_ACTIVE" if assignment.requirement == "REQUIRED" else "OPTIONAL_ACTIVE"


class RuntimeAssignmentProducer:
    """Writes three independent append-only streams; it never executes work."""

    def __init__(self, authority_path: str | Path = DEFAULT_AUTHORITY_LOG_PATH, assignment_path: str | Path = DEFAULT_ASSIGNMENT_LOG_PATH, lifecycle_path: str | Path = DEFAULT_LIFECYCLE_LOG_PATH, source_instance_id: str | None = None):
        self.authority_path = Path(authority_path)
        self.assignment_path = Path(assignment_path)
        self.lifecycle_path = Path(lifecycle_path)
        self.source_instance_id = source_instance_id or f"assignment-runtime-{uuid4()}"
        self._sequences = {"authority": 0, "assignment": 0, "lifecycle": 0}

    def grant_authority(self, *, issuer_id: str, authorized_principal_id: str, authority_type: str, scope_id: str, source_id: str, source_type: str, valid_from: str, valid_until: str | None = None, evidence_reference: str | None = None, grant_id: str | None = None, timestamp: str | None = None) -> RuntimeAuthorityGrant:
        record = RuntimeAuthorityGrant(SCHEMA_VERSION, grant_id or f"grant-{uuid4()}", issuer_id, authorized_principal_id, authority_type, scope_id, valid_from, valid_until, timestamp or _now(), self._source(source_id, source_type, evidence_reference), self._next("authority"))
        self._append(self.authority_path, record, validate_grant, "authority")
        return record

    def assign_work(self, *, objective_id: str, work_id: str, assigned_actor_id: str, issuer_id: str, scope_id: str, requirement: str, authority_grant_id: str | None, source_id: str, source_type: str, evidence_reference: str | None = None, assignment_id: str | None = None, assignment_at: str | None = None) -> RuntimeWorkAssignment:
        record = RuntimeWorkAssignment(SCHEMA_VERSION, assignment_id or f"assignment-{uuid4()}", objective_id, work_id, assigned_actor_id, issuer_id, scope_id, requirement, assignment_at or _now(), authority_grant_id, self._source(source_id, source_type, evidence_reference), self._next("assignment"))
        self._append(self.assignment_path, record, validate_assignment, "assignment")
        return record

    def record_lifecycle(self, *, assignment_id: str, state: str, issuer_id: str, authority_grant_id: str | None, source_id: str, source_type: str, event_at: str | None = None, evidence_reference: str | None = None, event_id: str | None = None, delegate_actor_id: str | None = None, replacement_assignment_id: str | None = None) -> RuntimeAssignmentLifecycleEvent:
        record = RuntimeAssignmentLifecycleEvent(SCHEMA_VERSION, event_id or f"lifecycle-{uuid4()}", assignment_id, state, event_at or _now(), issuer_id, authority_grant_id, self._source(source_id, source_type, evidence_reference), self._next("lifecycle"), delegate_actor_id, replacement_assignment_id)
        self._append(self.lifecycle_path, record, validate_lifecycle, "lifecycle")
        return record

    def _source(self, source_id: str, source_type: str, evidence_reference: str | None) -> RuntimeSourceAttribution:
        return RuntimeSourceAttribution(source_id, source_type, self.source_instance_id, evidence_reference)

    def _next(self, stream: str) -> int:
        self._sequences[stream] += 1
        return self._sequences[stream]

    def _append(self, path: Path, record, validator, stream: str) -> None:
        issues = validator(record)
        if issues:
            self._sequences[stream] -= 1
            raise ValueError(",".join(issues))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")) + "\n")


def load_assignment_evidence(authority_path: str | Path, assignment_path: str | Path, lifecycle_path: str | Path) -> AssignmentEvidenceReport:
    grants, grant_issues = _load(authority_path, RuntimeAuthorityGrant, validate_grant, "authority", "grant_id")
    assignments, assignment_issues = _load(assignment_path, RuntimeWorkAssignment, validate_assignment, "assignment", "assignment_id")
    lifecycle, lifecycle_issues = _load(lifecycle_path, RuntimeAssignmentLifecycleEvent, validate_lifecycle, "lifecycle", "event_id")
    issues = list(grant_issues + assignment_issues + lifecycle_issues)
    assignment_ids = {item.assignment_id for item in assignments}
    for event in lifecycle:
        if event.assignment_id not in assignment_ids:
            issues.append(f"UNKNOWN_ASSIGNMENT:{event.event_id}")
        elif lifecycle_authority_status(event, next(item for item in assignments if item.assignment_id == event.assignment_id), grants) != "VALID":
            issues.append(f"UNAUTHORIZED_LIFECYCLE:{event.event_id}")
    return AssignmentEvidenceReport(tuple(grants), tuple(assignments), tuple(lifecycle), tuple(sorted(set(issues))))


def to_research_authority(grant: RuntimeAuthorityGrant):
    from factual_context_research import Source, VerificationState
    from ethos_required_work_research import Attribution, AuthorityClaim
    attribution = Attribution(_source_enum(grant.source.source_type), grant.source.source_instance_id, grant.scope_id, grant.timestamp, VerificationState.ASSERTED, _research_reference(grant.source))
    return AuthorityClaim(grant.grant_id, grant.authorized_principal_id, grant.authority_type, "CONFIRMED" if not validate_grant(grant) else "UNKNOWN", attribution)


def to_research_assignment(assignment: RuntimeWorkAssignment):
    from factual_context_research import VerificationState
    from ethos_required_work_research import Attribution, RequiredWorkAssignment
    attribution = Attribution(_source_enum(assignment.source.source_type), assignment.source.source_instance_id, assignment.scope_id, assignment.assignment_at, VerificationState.ASSERTED, _research_reference(assignment.source))
    return RequiredWorkAssignment(assignment.assignment_id, assignment.objective_id, assignment.work_id, assignment.assigned_actor_id, assignment.issuer_id, assignment.requirement, assignment.assignment_at, attribution, assignment.authority_grant_id)


def to_research_lifecycle(event: RuntimeAssignmentLifecycleEvent, assignment: RuntimeWorkAssignment):
    from factual_context_research import VerificationState
    from ethos_required_work_research import AssignmentLifecycleClaim, Attribution
    attribution = Attribution(_source_enum(event.source.source_type), event.source.source_instance_id, assignment.scope_id, event.event_at, VerificationState.ASSERTED, _research_reference(event.source))
    return AssignmentLifecycleClaim(event.event_id, event.assignment_id, event.state, attribution, event.delegate_actor_id)


def _load(path, cls, validator, stream, identity):
    values, issues = [], []
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        # Empty lifecycle (or not-yet-used) streams are valid append-only history.
        return [], []
    except OSError as error:
        return [], [f"READ_ERROR:{stream}:{error}"]
    for number, line in enumerate(lines, 1):
        try:
            raw = json.loads(line)
            raw["source"] = RuntimeSourceAttribution(**raw["source"])
            value = cls(**raw)
        except Exception:
            issues.append(f"MALFORMED_ENTRY:{stream}:{number}")
            continue
        issues.extend(f"{issue}:{stream}:{number}" for issue in validator(value))
        values.append(value)
    ids = [getattr(item, identity) for item in values]
    if len(ids) != len(set(ids)):
        issues.append(f"DUPLICATE_ID:{stream}")
    for instance in {item.source.source_instance_id for item in values}:
        stream_values = [item for item in values if item.source.source_instance_id == instance]
        if [item.sequence_id for item in stream_values] != list(range(1, len(stream_values) + 1)):
            issues.append(f"INVALID_SEQUENCE_ORDER:{stream}:{instance}")
        timestamp_name = "assignment_at" if stream == "assignment" else "event_at" if stream == "lifecycle" else "timestamp"
        try:
            times = [_time(getattr(item, timestamp_name)) for item in stream_values]
            if any(left > right for left, right in zip(times, times[1:])):
                issues.append(f"INVALID_CHRONOLOGY:{stream}:{instance}")
        except ValueError:
            issues.append(f"INVALID_CHRONOLOGY:{stream}:{instance}")
    return values, issues


def _common_issues(record, identity, scope, timestamp):
    issues = []
    if record.schema_version != SCHEMA_VERSION:
        issues.append("UNSUPPORTED_SCHEMA")
    if not identity or not scope or record.sequence_id < 1:
        issues.append("MALFORMED")
    if not all((record.source.source_id, record.source.source_type, record.source.source_instance_id)):
        issues.append("INVALID_SOURCE")
    try:
        _time(timestamp)
    except ValueError:
        issues.append("INVALID_TIMESTAMP")
    return issues


def _valid_interval(start, end):
    try:
        return end is None or _time(start) <= _time(end)
    except ValueError:
        return False


def _before_or_equal(left, right):
    try:
        return _time(left) <= _time(right)
    except ValueError:
        return False


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _source_enum(value):
    from factual_context_research import Source
    aliases = {"CONTROLLER": Source.SYSTEM_ASSERTION, "AGENT": Source.MODEL_ASSERTION}
    return aliases.get(value, Source(value) if value in Source._value2member_map_ else Source.UNKNOWN_SOURCE)


def _research_reference(source: RuntimeSourceAttribution) -> str:
    """Keep runtime source identity in the older contract's sole reference field."""
    suffix = source.evidence_reference or ""
    return f"runtime-source:{source.source_id};source-type:{source.source_type};reference:{suffix}"

"""Neutral append-only runtime decision recorder; no gate or regulator authority."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

SCHEMA_VERSION = "ETHOS_RUNTIME_DECISION_RECORDER_V1"
DEFAULT_DECISION_LOG_PATH = Path(__file__).with_name("evidence") / "runtime_decisions.jsonl"


@dataclass(frozen=True)
class RuntimeActionCandidate:
    """An action considered at the decision boundary, with its own source."""

    action_id: str
    action_kind: str
    candidate_source: str


@dataclass(frozen=True)
class RuntimeDecisionRecord:
    schema_version: str
    decision_id: str
    sequence_id: int
    timestamp: str
    source_instance_id: str
    actor_id: str
    objective_id: str
    scope_id: str
    candidates: tuple[RuntimeActionCandidate, ...]
    selected_action_id: str
    candidate_source: str
    recorder_source: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["candidates"] = [asdict(item) for item in self.candidates]
        return data


@dataclass(frozen=True)
class DecisionLogReport:
    records: tuple[RuntimeDecisionRecord, ...]
    issues: tuple[str, ...]


def validate(record: RuntimeDecisionRecord) -> tuple[str, ...]:
    """Validate shape only; it makes no claim that a caller is authoritative."""
    issues: list[str] = []
    if record.schema_version != SCHEMA_VERSION:
        issues.append("UNSUPPORTED_SCHEMA")
    if not all((
        record.decision_id, record.timestamp, record.source_instance_id,
        record.actor_id, record.objective_id, record.scope_id,
        record.candidate_source, record.recorder_source,
    )):
        issues.append("MISSING_IDENTITY_OR_SOURCE")
    if record.sequence_id < 1:
        issues.append("INVALID_SEQUENCE")
    action_ids = [item.action_id for item in record.candidates]
    if not action_ids:
        issues.append("EMPTY_CANDIDATES")
    if any(not item.action_id or not item.action_kind or not item.candidate_source
           for item in record.candidates):
        issues.append("MALFORMED_CANDIDATE")
    if len(action_ids) != len(set(action_ids)):
        issues.append("DUPLICATE_CANDIDATE_ID")
    if record.selected_action_id not in action_ids:
        issues.append("SELECTED_ACTION_NOT_CANDIDATE")
    try:
        _time(record.timestamp)
    except ValueError:
        issues.append("INVALID_TIMESTAMP")
    return tuple(sorted(set(issues)))


class RuntimeDecisionRecorder:
    """Append decision facts before execution with a fresh source ID per process.

    A restart intentionally receives a new ``source_instance_id`` by default,
    so its sequence starts at one without conflating histories. Supplying the
    same ID after restart is unsupported and loader validation will flag it.
    """

    def __init__(
        self,
        path: str | Path = DEFAULT_DECISION_LOG_PATH,
        recorder_source: str = "ethos-runtime-decision-recorder",
        source_instance_id: str | None = None,
    ):
        self.path = Path(path)
        self.recorder_source = recorder_source
        self.source_instance_id = source_instance_id or f"runtime-{uuid4()}"
        self._sequence = 0

    def record_decision(
        self,
        *,
        actor_id: str,
        objective_id: str,
        scope_id: str,
        candidates: tuple[RuntimeActionCandidate, ...],
        selected_action_id: str,
        candidate_source: str,
        decision_id: str | None = None,
        timestamp: str | None = None,
    ) -> RuntimeDecisionRecord:
        """Persist a candidate set and selected member; it never executes either."""
        self._sequence += 1
        record = RuntimeDecisionRecord(
            SCHEMA_VERSION,
            decision_id or f"decision-{uuid4()}",
            self._sequence,
            timestamp or datetime.now(timezone.utc).isoformat(),
            self.source_instance_id,
            actor_id,
            objective_id,
            scope_id,
            tuple(candidates),
            selected_action_id,
            candidate_source,
            self.recorder_source,
        )
        issues = validate(record)
        if issues:
            self._sequence -= 1
            raise ValueError(",".join(issues))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")) + "\n")
        return record


def load_decision_log(path: str | Path) -> DecisionLogReport:
    """Read and validate JSONL while retaining valid entries for inspection."""
    records: list[RuntimeDecisionRecord] = []
    issues: list[str] = []
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return DecisionLogReport((), (f"READ_ERROR:{error}",))
    for line_number, line in enumerate(lines, 1):
        try:
            raw = json.loads(line)
            candidates = tuple(RuntimeActionCandidate(**item) for item in raw.pop("candidates"))
            record = RuntimeDecisionRecord(candidates=candidates, **raw)
        except Exception:
            issues.append(f"MALFORMED_ENTRY:{line_number}")
            continue
        issues.extend(f"{issue}:{line_number}" for issue in validate(record))
        records.append(record)

    if len({item.decision_id for item in records}) != len(records):
        issues.append("DUPLICATE_DECISION_ID")
    for instance in {item.source_instance_id for item in records}:
        stream = [item for item in records if item.source_instance_id == instance]
        sequences = [item.sequence_id for item in stream]
        if len(set(sequences)) != len(sequences):
            issues.append(f"DUPLICATE_SEQUENCE_ID:{instance}")
        if sequences != list(range(1, len(stream) + 1)):
            issues.append(f"INVALID_SEQUENCE_ORDER:{instance}")
        try:
            times = [_time(item.timestamp) for item in stream]
        except ValueError:
            continue
        if any(left >= right for left, right in zip(times, times[1:])):
            issues.append(f"INVALID_CHRONOLOGY:{instance}")
    return DecisionLogReport(tuple(records), tuple(sorted(set(issues))))


def to_research_entry(record: RuntimeDecisionRecord):
    """Map only decision facts; availability, value, authority remain UNKNOWN."""
    from ethos_action_decision_research import (
        UNKNOWN, ActionCandidate, ActionDecisionRecord, SourceAttribution,
    )
    from ethos_decision_history_research import DecisionHistoryEntry

    source = SourceAttribution(
        record.candidate_source, record.source_instance_id, record.scope_id, record.timestamp,
    )
    candidates = tuple(
        ActionCandidate(item.action_id, record.objective_id, required_status=UNKNOWN, available=UNKNOWN)
        for item in record.candidates
    )
    decision = ActionDecisionRecord(
        record.decision_id, record.objective_id, candidates, record.selected_action_id, source,
    )
    return DecisionHistoryEntry(
        decision, record.actor_id, record.scope_id, record.sequence_id,
        record.timestamp, record.source_instance_id,
    )


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

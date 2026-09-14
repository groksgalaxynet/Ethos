"""Durable blocked-policy history and conservative scar consequence policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Sequence

from scar_service import ScarService


class HistoryInspectionError(ValueError):
    """A history database cannot safely be presented by the read-only viewer."""


_HISTORY_VIEW_COLUMNS = (
    "id", "evidence_id", "agent_id", "session_id", "timestamp", "proposal_type",
    "primary_policy_id", "policy_family", "policy_ids_json", "decision", "evidence_path",
    "repeat_count", "scar_created", "scar_id", "scar_severity", "scar_reason",
    "consequence_state", "consequence_status", "consequence_error",
)

_RECORD_COLUMNS = (
    "id", "evidence_id", "agent_id", "session_id", "timestamp", "proposal_type",
    "primary_policy_id", "policy_family", "policy_ids_json", "regulator_name",
    "regulator_vector", "decision", "evidence_path", "repeat_count", "scar_created",
    "scar_id", "scar_severity", "scar_reason", "consequence_state", "consequence_status",
    "consequence_error",
)


@dataclass(frozen=True)
class ConsequencePolicy:
    """Repeat thresholds; counts are per agent and normalized policy family."""

    minor_repeat_threshold: int = 2
    major_repeat_threshold: int = 4

    def __post_init__(self) -> None:
        if self.minor_repeat_threshold < 2:
            raise ValueError("minor_repeat_threshold must be at least 2")
        if self.major_repeat_threshold <= self.minor_repeat_threshold:
            raise ValueError("major_repeat_threshold must be greater than minor_repeat_threshold")


@dataclass(frozen=True)
class ViolationRecord:
    violation_id: str
    evidence_id: str
    agent_id: str
    session_id: str
    timestamp: str
    proposal_type: str
    primary_policy_id: str
    policy_family: str
    policy_ids: tuple[str, ...]
    regulator_name: str | None
    regulator_vector: str | None
    decision: str
    evidence_path: str
    repeat_count: int
    scar_created: bool
    scar_id: int | None
    scar_severity: str | None
    scar_reason: str | None
    consequence_state: str
    consequence_status: str
    consequence_error: str | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["policy_ids"] = list(self.policy_ids)
        return data


class ViolationHistory:
    """SQLite history keyed by evidence ID to make blocked-event replay idempotent."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def record(
        self,
        *,
        evidence_id: str,
        agent_id: str,
        session_id: str,
        timestamp: str,
        proposal_type: str,
        primary_policy_id: str,
        policy_ids: Sequence[str],
        decision: str,
        evidence_path: str,
    ) -> tuple[ViolationRecord, bool]:
        """Record one BLOCK or return its existing row when evidence is replayed."""
        existing = self.get_by_evidence_id(evidence_id)
        if existing is not None:
            return existing, False
        policy_family, regulator_name, regulator_vector = classify_policy(primary_policy_id)
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute(
                """INSERT INTO violations(
                    evidence_id, agent_id, session_id, timestamp, proposal_type,
                    primary_policy_id, policy_family, policy_ids_json, regulator_name,
                    regulator_vector, decision, evidence_path, scar_created, consequence_state,
                    consequence_status
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    evidence_id,
                    agent_id,
                    session_id,
                    timestamp,
                    proposal_type,
                    primary_policy_id,
                    policy_family,
                    json.dumps(list(policy_ids)),
                    regulator_name,
                    regulator_vector,
                    decision,
                    evidence_path,
                    0,
                    "WARNING",
                    "recorded",
                ),
            )
            violation_id = str(cursor.lastrowid)
            repeat_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM violations WHERE agent_id=? AND policy_family=?",
                    (agent_id, policy_family),
                ).fetchone()[0]
            )
            connection.execute(
                "UPDATE violations SET repeat_count=?, consequence_state=? WHERE id=?",
                (repeat_count, consequence_state_for(repeat_count), violation_id),
            )
            connection.commit()
        return self.get_by_evidence_id(evidence_id), True  # type: ignore[return-value]

    def update_consequence(
        self,
        evidence_id: str,
        *,
        scar_created: bool,
        scar_id: int | None,
        scar_severity: str | None,
        scar_reason: str | None = None,
        status: str,
        error: str | None = None,
    ) -> ViolationRecord:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """UPDATE violations SET scar_created=?, scar_id=?, scar_severity=?, scar_reason=?,
                    consequence_status=?, consequence_error=? WHERE evidence_id=?""",
                (int(scar_created), scar_id, scar_severity, scar_reason, status, error, evidence_id),
            )
            connection.commit()
        result = self.get_by_evidence_id(evidence_id)
        if result is None:
            raise RuntimeError("violation disappeared while updating consequence")
        return result

    def latest_scar_for(self, agent_id: str, policy_family: str) -> ViolationRecord | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                f"""SELECT {', '.join(_RECORD_COLUMNS)} FROM violations WHERE agent_id=? AND policy_family=?
                   AND scar_id IS NOT NULL ORDER BY id DESC LIMIT 1""",
                (agent_id, policy_family),
            ).fetchone()
        return self._from_row(row) if row is not None else None

    def get_by_evidence_id(self, evidence_id: str) -> ViolationRecord | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                f"SELECT {', '.join(_RECORD_COLUMNS)} FROM violations WHERE evidence_id=?", (evidence_id,)
            ).fetchone()
        return self._from_row(row) if row is not None else None

    def count(self) -> int:
        with sqlite3.connect(self.path) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM violations").fetchone()[0])

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS violations(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evidence_id TEXT NOT NULL UNIQUE,
                    agent_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    proposal_type TEXT NOT NULL,
                    primary_policy_id TEXT NOT NULL,
                    policy_family TEXT NOT NULL,
                    policy_ids_json TEXT NOT NULL,
                    regulator_name TEXT,
                    regulator_vector TEXT,
                    decision TEXT NOT NULL,
                    evidence_path TEXT NOT NULL,
                    repeat_count INTEGER NOT NULL DEFAULT 0,
                    scar_created INTEGER NOT NULL DEFAULT 0,
                    scar_id INTEGER,
                    scar_severity TEXT,
                    scar_reason TEXT,
                    consequence_state TEXT NOT NULL DEFAULT 'WARNING',
                    consequence_status TEXT NOT NULL,
                    consequence_error TEXT
                )"""
            )
            columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(violations)")}
            if "consequence_state" not in columns:
                connection.execute(
                    "ALTER TABLE violations ADD COLUMN consequence_state TEXT NOT NULL DEFAULT 'WARNING'"
                )
                connection.execute(
                    """UPDATE violations SET consequence_state=CASE
                        WHEN repeat_count >= 4 THEN 'MAJOR_SCAR'
                        WHEN repeat_count = 3 THEN 'REPEATED_AFTER_MINOR'
                        WHEN repeat_count = 2 THEN 'MINOR_SCAR'
                        ELSE 'WARNING'
                    END"""
                )
            connection.commit()

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> ViolationRecord:
        return ViolationRecord(
            violation_id=str(row[0]), evidence_id=row[1], agent_id=row[2], session_id=row[3],
            timestamp=row[4], proposal_type=row[5], primary_policy_id=row[6], policy_family=row[7],
            policy_ids=tuple(json.loads(row[8])), regulator_name=row[9], regulator_vector=row[10],
            decision=row[11], evidence_path=row[12], repeat_count=int(row[13]),
            scar_created=bool(row[14]), scar_id=row[15], scar_severity=row[16],
            scar_reason=row[17], consequence_state=row[18], consequence_status=row[19],
            consequence_error=row[20],
        )


class ConsequenceService:
    """Central repeat-to-scar policy; analyzers never call this service."""

    def __init__(
        self,
        history: ViolationHistory,
        scars: ScarService,
        policy: ConsequencePolicy | None = None,
    ) -> None:
        self.history = history
        self.scars = scars
        self.policy = policy or ConsequencePolicy()

    def apply_block(self, **details: Any) -> dict[str, Any]:
        record, inserted = self.history.record(**details)
        if not inserted:
            return self._to_evidence(record, replayed=True)
        severity = self._severity_for(record.repeat_count)
        if severity is None:
            existing = self.history.latest_scar_for(record.agent_id, record.policy_family)
            if existing is not None:
                record = self.history.update_consequence(
                    record.evidence_id,
                    scar_created=False,
                    scar_id=existing.scar_id,
                    scar_severity=existing.scar_severity,
                    scar_reason=existing.scar_reason,
                    status="recorded_existing_scar",
                )
            return self._to_evidence(record)
        reason = (
            f"Ethos repeated blocked policy {record.primary_policy_id}; "
            f"occurrence {record.repeat_count}; evidence {record.evidence_id}"
        )
        try:
            scar = self.scars.create_scar(severity, reason)
        except Exception as error:  # The BLOCK and history must survive scar persistence failure.
            record = self.history.update_consequence(
                record.evidence_id,
                scar_created=False,
                scar_id=None,
                scar_severity=None,
                scar_reason=None,
                status="scar_persistence_failed",
                error=str(error),
            )
            return self._to_evidence(record)
        record = self.history.update_consequence(
            record.evidence_id,
            scar_created=True,
            scar_id=scar.scar_id,
            scar_severity=scar.severity.title(),
            scar_reason=reason,
            status="scar_created",
        )
        return self._to_evidence(record)

    def _severity_for(self, repeat_count: int) -> str | None:
        if repeat_count == self.policy.major_repeat_threshold:
            return "major"
        if repeat_count == self.policy.minor_repeat_threshold:
            return "minor"
        return None

    def _to_evidence(self, record: ViolationRecord, replayed: bool = False) -> dict[str, Any]:
        return {
            "violation_recorded": True,
            "violation_id": record.violation_id,
            "repeat_count": record.repeat_count,
            "primary_policy_id": record.primary_policy_id,
            "policy_family": record.policy_family,
            "history_policy": {
                "minor_repeat_threshold": self.policy.minor_repeat_threshold,
                "major_repeat_threshold": self.policy.major_repeat_threshold,
            },
            "scar_created": record.scar_created,
            "scar_id": record.scar_id,
            "scar_severity": record.scar_severity,
            "scar_reason": record.scar_reason,
            "state": record.consequence_state,
            "status": record.consequence_status,
            "error": record.consequence_error,
            "replayed": replayed,
        }


def consequence_state_for(repeat_count: int) -> str:
    """Return the bounded historical classification; it never changes the gate decision."""
    if repeat_count >= 4:
        return "MAJOR_SCAR"
    if repeat_count == 3:
        return "REPEATED_AFTER_MINOR"
    if repeat_count == 2:
        return "MINOR_SCAR"
    return "WARNING"


def classify_policy(policy_id: str) -> tuple[str, str | None, str | None]:
    """Use regulator family or exact bootstrap policy as the repeat identity."""
    parts = policy_id.split(".")
    if len(parts) >= 3 and parts[0] == "REGULATOR":
        return ".".join(parts[:2]), parts[1].lower(), ".".join(parts[2:])
    return policy_id, None, None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_violation_history(
    path: str | Path,
    *,
    recent: int = 20,
    agent_id: str | None = None,
    policy_family: str | None = None,
    session_id: str | None = None,
    evidence_id: str | None = None,
) -> dict[str, Any]:
    """Read stored consequence state without creating or changing any database files."""
    if recent < 1:
        raise HistoryInspectionError("--recent must be at least 1.")
    history_path = Path(path)
    if not history_path.is_file():
        raise HistoryInspectionError(f"Violation history DB does not exist: {history_path}")

    try:
        with _read_only_connection(history_path) as connection:
            _validate_history_schema(connection)
            summary = _history_summary(connection)
            where, params = _history_filters(agent_id, policy_family, session_id, evidence_id)
            rows = connection.execute(
                f"SELECT {', '.join(_HISTORY_VIEW_COLUMNS)} FROM violations{where} "
                "ORDER BY id DESC LIMIT ?",
                (*params, recent),
            ).fetchall()
    except sqlite3.Error as error:
        raise HistoryInspectionError(f"Could not read violation history safely: {error}") from error

    return {
        "summary": summary,
        "filters": {
            "recent": recent,
            "agent_id": agent_id,
            "policy_family": policy_family,
            "session_id": session_id,
            "evidence_id": evidence_id,
        },
        "violations": [_history_row_to_dict(row) for row in rows],
    }


def _read_only_connection(path: Path) -> sqlite3.Connection:
    """Open an existing SQLite database in URI read-only mode."""
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def _validate_history_schema(connection: sqlite3.Connection) -> None:
    columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(violations)")}
    missing = [column for column in _HISTORY_VIEW_COLUMNS if column not in columns]
    if missing:
        raise HistoryInspectionError(
            "Unsupported violation-history schema; missing columns: " + ", ".join(missing)
        )


def _history_filters(
    agent_id: str | None,
    policy_family: str | None,
    session_id: str | None,
    evidence_id: str | None = None,
) -> tuple[str, list[str]]:
    clauses: list[str] = []
    params: list[str] = []
    for column, value in (
        ("agent_id", agent_id),
        ("policy_family", policy_family),
        ("session_id", session_id),
        ("evidence_id", evidence_id),
    ):
        if value is not None:
            clauses.append(f"{column}=?")
            params.append(value)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


def _history_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    family_rows = connection.execute(
        "SELECT policy_family, COUNT(*) FROM violations GROUP BY policy_family ORDER BY policy_family"
    ).fetchall()
    highest_rows = connection.execute(
        """SELECT agent_id, policy_family, MAX(repeat_count) FROM violations
           GROUP BY agent_id, policy_family ORDER BY MAX(repeat_count) DESC, agent_id, policy_family"""
    ).fetchall()
    return {
        "total_stored_violations": int(connection.execute("SELECT COUNT(*) FROM violations").fetchone()[0]),
        "count_by_policy_family": {str(family): int(count) for family, count in family_rows},
        "count_with_scars": int(
            connection.execute("SELECT COUNT(*) FROM violations WHERE scar_id IS NOT NULL").fetchone()[0]
        ),
        "minor_scar_count": int(
            connection.execute(
                "SELECT COUNT(*) FROM violations WHERE lower(scar_severity)='minor'"
            ).fetchone()[0]
        ),
        "major_scar_count": int(
            connection.execute(
                "SELECT COUNT(*) FROM violations WHERE lower(scar_severity)='major'"
            ).fetchone()[0]
        ),
        "highest_repeat_by_agent_policy_family": [
            {"agent_id": agent, "policy_family": family, "repeat_count": int(repeat_count)}
            for agent, family, repeat_count in highest_rows
        ],
    }


def _history_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    result = dict(zip(_HISTORY_VIEW_COLUMNS, row, strict=True))
    result["violation_id"] = str(result.pop("id"))
    result["scar_created"] = bool(result["scar_created"])
    result["repeat_count"] = int(result["repeat_count"])
    try:
        result["policy_ids"] = json.loads(result.pop("policy_ids_json"))
    except (TypeError, json.JSONDecodeError):
        result["policy_ids"] = []
        result.pop("policy_ids_json", None)
    return result

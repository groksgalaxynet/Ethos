"""Read-only projection of current ETHOS consequence history for ScarGUI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from evidence_packet import EvidencePacketError, find_evidence_record, format_evidence_packet, packet_from_history_record
from scar_service import ScarService
from violation_history import HistoryInspectionError, read_violation_history


CURRENT_STATES = frozenset({"WARNING", "MINOR_SCAR", "REPEATED_AFTER_MINOR", "MAJOR_SCAR"})
DEFAULT_HISTORY_PATH = Path(__file__).with_name("evidence") / "proposal_gate.violations.db"


@dataclass(frozen=True)
class ScarGuiRow:
    """One persisted BLOCK record, projected without changing consequence data."""

    violation_id: str
    evidence_id: str
    agent_id: str
    policy_family: str
    decision: str
    occurrence: int
    consequence_state: str
    timestamp: str
    scar_id: int | None
    scar_severity: str | None
    scar_reason: str | None
    reason: str | None
    scar_metadata: Mapping[str, Any] | None
    evidence_path: str


class ScarGuiAdapter:
    """The GUI's sole read-only boundary to existing history, scars, and evidence."""

    def __init__(self, history_path: str | Path = DEFAULT_HISTORY_PATH) -> None:
        self.history_path = Path(history_path)

    def load(self, *, recent: int = 200) -> tuple[list[ScarGuiRow], dict[str, Any], str | None]:
        """Return persisted rows, summary, and a display-safe error; never initialize storage."""
        try:
            view = read_violation_history(self.history_path, recent=recent)
        except HistoryInspectionError as error:
            return [], {}, str(error)
        rows = [self._row(record) for record in view["violations"] if isinstance(record, Mapping)]
        return rows, dict(view["summary"]), None

    def details(self, row: ScarGuiRow) -> str:
        """Format only stored detail fields, including evidence when it remains available."""
        record = {
            "violation_id": row.violation_id,
            "evidence_id": row.evidence_id,
            "agent_id": row.agent_id,
            "policy_family": row.policy_family,
            "decision": row.decision,
            "repeat_count": row.occurrence,
            "consequence_state": row.consequence_state,
            "timestamp": row.timestamp,
            "scar_id": row.scar_id,
            "scar_severity": row.scar_severity,
            "scar_reason": row.scar_reason,
            "scar_created": row.scar_id is not None,
            "evidence_path": row.evidence_path,
        }
        evidence = self._evidence_for(record)
        text = format_evidence_packet(packet_from_history_record(record, evidence))
        if row.scar_metadata is not None:
            text += "\n\nSCAR LEDGER METADATA\n" + "\n".join(
                f"{key}: {value}" for key, value in row.scar_metadata.items()
            )
        elif row.scar_id is not None:
            text += "\n\nScar ledger metadata unavailable."
        if evidence is None:
            text += "\nEvidence details unavailable; no value was inferred."
        return text

    def _row(self, record: Mapping[str, Any]) -> ScarGuiRow:
        scar_id = record.get("scar_id")
        normalized_scar_id = scar_id if isinstance(scar_id, int) else None
        evidence = self._evidence_for(record)
        return ScarGuiRow(
            violation_id=str(record.get("violation_id", "unavailable")),
            evidence_id=str(record.get("evidence_id", "unavailable")),
            agent_id=str(record.get("agent_id", "unavailable")),
            policy_family=str(record.get("policy_family", "unavailable")),
            decision=str(record.get("decision", "unavailable")),
            occurrence=int(record.get("repeat_count", 0)),
            consequence_state=str(record.get("consequence_state", "WARNING")),
            timestamp=str(record.get("timestamp", "unavailable")),
            scar_id=normalized_scar_id,
            scar_severity=_optional_text(record.get("scar_severity")),
            scar_reason=_optional_text(record.get("scar_reason")),
            reason=_optional_text(evidence.get("reason")) if evidence else None,
            scar_metadata=self._scar_metadata(record, normalized_scar_id),
            evidence_path=str(record.get("evidence_path", "")),
        )

    @staticmethod
    def _evidence_for(record: Mapping[str, Any]) -> dict[str, Any] | None:
        evidence_path = record.get("evidence_path")
        evidence_id = record.get("evidence_id")
        if not isinstance(evidence_path, str) or not evidence_path or not isinstance(evidence_id, str):
            return None
        try:
            return find_evidence_record(evidence_path, evidence_id)
        except EvidencePacketError:
            return None

    @staticmethod
    def _scar_metadata(record: Mapping[str, Any], scar_id: int | None) -> dict[str, Any] | None:
        evidence_path = record.get("evidence_path")
        if scar_id is None or not isinstance(evidence_path, str) or not evidence_path:
            return None
        evidence = Path(evidence_path)
        scar = ScarService(evidence.parent / f"{evidence.stem}_scar_runtime").get_scar_readonly(scar_id)
        if scar is None:
            return None
        return {"scar_id": scar.scar_id, "timestamp": scar.timestamp, "severity": scar.severity,
                "reason": scar.reason, "file": scar.file, "bytes": scar.bytes, "hash": scar.hash}


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None

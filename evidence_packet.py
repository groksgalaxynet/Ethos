"""Deterministic, read-only audit packets built from stored Ethos evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


EVIDENCE_PACKET_SCHEMA_V1 = "ETHOS_EVIDENCE_PACKET_V1"


class EvidencePacketError(ValueError):
    """A requested stored evidence packet cannot safely be assembled."""


def canonical_packet_json(packet: Mapping[str, Any]) -> str:
    """Serialize a packet with stable ordering and no export-time fields."""
    return json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def evidence_packet_digest(packet: Mapping[str, Any]) -> str:
    """Return the reproducible SHA-256 digest of canonical packet bytes."""
    return hashlib.sha256(canonical_packet_json(packet).encode("utf-8")).hexdigest()


def find_evidence_record(path: str | Path, evidence_id: str) -> dict[str, Any] | None:
    """Find one stored JSONL decision by its existing evidence identifier."""
    if not evidence_id.strip():
        raise EvidencePacketError("--evidence-id must be non-empty.")
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise EvidencePacketError(f"Could not read evidence JSONL: {error}") from error
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("evidence_id") == evidence_id:
            return record
    return None


def packet_from_evidence_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project a stored ALLOW or BLOCK decision without inferring missing state."""
    evidence_id = _required_text(record, "evidence_id")
    decision = _required_text(record, "decision")
    proposal = _mapping(record.get("proposal"))
    raw_consequence = _mapping(record.get("consequence"))
    policies = _string_list(record.get("policy_ids"))
    event = _omit_unavailable(
        {
            "evidence_id": evidence_id,
            "timestamp": record.get("timestamp"),
            "decision": decision,
            "agent_id": record.get("agent_id", proposal.get("agent_id")),
            "session_id": record.get("session_id", proposal.get("session_id")),
            "proposal_type": proposal.get("proposal_type"),
            "primary_policy_id": policies[0] if policies else None,
            "policy_ids": policies or None,
            "policy_family": raw_consequence.get("policy_family"),
            "reason": record.get("reason"),
        }
    )
    packet: dict[str, Any] = {
        "schema_version": EVIDENCE_PACKET_SCHEMA_V1,
        "event": event,
        "recorded_evidence": dict(record),
    }
    consequence = _evidence_consequence(record.get("consequence"))
    if consequence is not None:
        packet["consequence"] = consequence
    return packet


def packet_from_history_record(
    record: Mapping[str, Any], evidence_record: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Project a stored violation row and optional matching JSONL decision record."""
    evidence_id = _required_text(record, "evidence_id")
    persisted_evidence = _mapping(evidence_record)
    event = _omit_unavailable(
        {
            "violation_id": record.get("violation_id"),
            "evidence_id": evidence_id,
            "timestamp": record.get("timestamp"),
            "decision": record.get("decision"),
            "agent_id": record.get("agent_id"),
            "session_id": record.get("session_id"),
            "proposal_type": record.get("proposal_type"),
            "policy_family": record.get("policy_family"),
            "primary_policy_id": record.get("primary_policy_id"),
            "policy_ids": record.get("policy_ids"),
            "evidence_path": record.get("evidence_path"),
            "reason": persisted_evidence.get("reason"),
        }
    )
    consequence = _omit_unavailable(
        {
            "state": record.get("consequence_state"),
            "occurrence": record.get("repeat_count"),
            "status": record.get("consequence_status"),
            "error": record.get("consequence_error"),
            "scar": _omit_unavailable(
                {
                    "created": record.get("scar_created"),
                    "id": record.get("scar_id"),
                    "severity": record.get("scar_severity"),
                    "reason": record.get("scar_reason"),
                    "metadata": record.get("scar_metadata"),
                }
            ),
        }
    )
    packet: dict[str, Any] = {
        "schema_version": EVIDENCE_PACKET_SCHEMA_V1,
        "event": event,
        "consequence": consequence,
        "history_link": {"violation_id": str(record.get("violation_id", "unavailable")), "evidence_id": evidence_id},
    }
    if evidence_record is not None:
        packet["recorded_evidence"] = dict(evidence_record)
    return packet


def format_evidence_packet(packet: Mapping[str, Any], digest: str | None = None) -> str:
    """Render stored packet fields as a compact copyable audit summary."""
    event = _mapping(packet.get("event"))
    consequence = _mapping(packet.get("consequence"))
    scar = _mapping(consequence.get("scar"))
    lines = ["ETHOS EVIDENCE PACKET"]
    for label, key in (
        ("Agent", "agent_id"),
        ("Policy family", "policy_family"),
        ("Decision", "decision"),
        ("Reason", "reason"),
        ("Occurrence", "occurrence"),
        ("Consequence state", "state"),
        ("Recorded evidence", "evidence_id"),
        ("Timestamp", "timestamp"),
    ):
        value = consequence.get(key) if key in {"occurrence", "state"} else event.get(key)
        if value is not None:
            lines.append(f"{label}: {value}")
    if scar:
        lines.append(
            "Scar: " + (
                f"{scar.get('severity', 'unavailable')} #{scar.get('id', 'unavailable')}"
                if scar.get("id") is not None else "none"
            )
        )
    if digest is not None:
        lines.append(f"SHA-256: {digest}")
    return "\n".join(lines)


def _evidence_consequence(value: Any) -> dict[str, Any] | None:
    consequence = _mapping(value)
    if not consequence.get("violation_recorded"):
        return None
    return _omit_unavailable(
        {
            "violation_id": consequence.get("violation_id"),
            "state": consequence.get("state"),
            "occurrence": consequence.get("repeat_count"),
            "status": consequence.get("status"),
            "error": consequence.get("error"),
            "replayed": consequence.get("replayed"),
            "scar": _omit_unavailable(
                {
                    "created": consequence.get("scar_created"),
                    "id": consequence.get("scar_id"),
                    "severity": consequence.get("scar_severity"),
                    "reason": consequence.get("scar_reason"),
                }
            ),
        }
    )


def _required_text(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise EvidencePacketError(f"Stored record has no usable {key}.")
    return value


def _omit_unavailable(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list | tuple) else []

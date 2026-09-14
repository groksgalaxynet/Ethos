"""Operator-facing, proposal-only CLI for the existing Ethos gate.

This module presents saved proposals, local Ollama proposals, and stored
evidence. It deliberately contains no action executor.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from evidence_packet import (
    EvidencePacketError,
    evidence_packet_digest,
    find_evidence_record,
    format_evidence_packet,
    packet_from_evidence_record,
    packet_from_history_record,
)
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore
from ollama_proposal_adapter import OllamaProposalAdapter
from scar_service import ScarService
from violation_history import HistoryInspectionError, read_violation_history


DEFAULT_EVIDENCE_PATH = Path(__file__).with_name("evidence") / "proposal_gate.jsonl"
REGULATOR_ORDER = ("greed", "pride", "envy")


class CliError(ValueError):
    """Expected operator-input failure that must not crash the CLI."""


def load_proposal(path: str | Path) -> Mapping[str, Any]:
    """Read one proposal as inert JSON data; it is never interpreted as code."""
    proposal_path = Path(path)
    try:
        value = json.loads(proposal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CliError(f"Could not read proposal JSON: {error}") from error
    if not isinstance(value, Mapping):
        raise CliError("Proposal JSON must contain a top-level object.")
    return value


def read_evidence(
    path: str | Path,
    recent: int = 1,
    session_id: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Safely read recent evidence, tolerating blank or malformed historic lines."""
    if recent < 1:
        raise CliError("--recent must be at least 1.")
    evidence_path = Path(path)
    try:
        lines = evidence_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise CliError(f"Could not read evidence JSONL: {error}") from error

    records: list[dict[str, Any]] = []
    skipped = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if not isinstance(record, dict):
            skipped += 1
            continue
        if session_id is not None and str(record.get("session_id", "")) != session_id:
            continue
        records.append(record)
    return records[-recent:], skipped


def inspect_saved_proposal(
    proposal_path: str | Path,
    evidence_path: str | Path = DEFAULT_EVIDENCE_PATH,
) -> dict[str, Any]:
    """Load inert saved JSON, inspect it through the central gate, return evidence."""
    proposal = load_proposal(proposal_path)
    return _inspect_and_read_record(proposal, evidence_path)


def inspect_ollama_task(
    task: str,
    model: str,
    evidence_path: str | Path = DEFAULT_EVIDENCE_PATH,
    agent_id: str = "ethos-cli-ollama",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Ask local Ollama for a proposal, then inspect it; never execute it."""
    proposal = OllamaProposalAdapter(model=model).propose(task, agent_id, session_id)
    return _inspect_and_read_record(proposal, evidence_path)


def _inspect_and_read_record(proposal: Any, evidence_path: str | Path) -> dict[str, Any]:
    store = JsonlEvidenceStore(evidence_path)
    decision = EthosProposalGate(store).inspect(proposal)
    records, skipped = read_evidence(store.path, recent=1)
    if not records:
        raise CliError("The gate did not produce a readable evidence record.")
    record = records[0]
    if skipped:
        record = dict(record)
        record["cli_skipped_evidence_lines"] = skipped
    if record.get("evidence_id") != decision.evidence_id:
        raise CliError("The latest evidence record did not match the gate decision.")
    record = dict(record)
    record["cli_evidence_path"] = str(store.path)
    return record


def format_record(record: Mapping[str, Any]) -> str:
    """Render a compact, backward-compatible operator view of one evidence record."""
    proposal = _mapping(record.get("proposal"))
    diagnostics = _mapping(proposal.get("adapter_diagnostics"))
    regulators = _mapping(record.get("regulators"))
    consequence = _mapping(record.get("consequence"))
    policies = _string_list(record.get("policy_ids"))
    primary = policies[0] if policies else "unavailable"

    lines = ["SESSION"]
    lines.extend(
        (
            f"Agent: {record.get('agent_id', proposal.get('agent_id', 'unavailable'))}",
            f"Session ID: {record.get('session_id', proposal.get('session_id', 'unavailable'))}",
            f"Task: {record.get('task', proposal.get('task', 'unavailable'))}",
        )
    )

    lines.extend(("", "ADAPTER"))
    if diagnostics:
        for key in (
            "contract_version",
            "model",
            "schema_mode",
            "parse_status",
            "validation_status",
            "repair_applied",
        ):
            if key in diagnostics:
                lines.append(f"{key}: {diagnostics[key]}")
        issues = _string_list(diagnostics.get("issues"))
        lines.append(f"issues: {', '.join(issues) if issues else 'none'}")
    else:
        lines.append("Adapter diagnostics: unavailable (saved or older evidence record).")

    lines.extend(("", "PROPOSAL"))
    lines.extend(
        (
            f"Type: {proposal.get('proposal_type', 'unavailable')}",
            f"Target: {proposal.get('target', 'unavailable')}",
            f"Arguments: {_compact_json(proposal.get('arguments', 'unavailable'))}",
            f"Exposed rationale: {proposal.get('exposed_reasoning', 'unavailable')}",
        )
    )

    lines.extend(("", "REGULATORS"))
    for name in REGULATOR_ORDER:
        lines.extend(_format_regulator(name, _mapping(regulators.get(name))))

    lines.extend(("", "CONSEQUENCE"))
    lines.extend(_format_consequence(consequence))

    lines.extend(("", "DECISION"))
    lines.extend(
        (
            f"Decision: {record.get('decision', 'unavailable')}",
            f"Primary policy: {primary}",
            "Contributing policies: " + (", ".join(policies) if policies else "unavailable"),
            f"Reason: {record.get('reason', 'unavailable')}",
            "Execution: " + _execution_message(str(record.get("decision", ""))),
        )
    )
    human = record.get("human_readable")
    if human:
        lines.extend(("", "HUMAN-READABLE EXPLANATION", str(human)))

    lines.extend(("", "EVIDENCE"))
    lines.extend(
        (
            f"Evidence ID: {record.get('evidence_id', 'unavailable')}",
            f"Timestamp: {record.get('timestamp', 'unavailable')}",
        )
    )
    if record.get("cli_evidence_path"):
        lines.append(f"Evidence path: {record['cli_evidence_path']}")
    if record.get("cli_skipped_evidence_lines"):
        lines.append(f"Malformed historic JSONL lines skipped: {record['cli_skipped_evidence_lines']}")
    return "\n".join(lines)


def _format_regulator(name: str, analysis: Mapping[str, Any]) -> list[str]:
    label = name.upper()
    if not analysis:
        return [f"{label}: unavailable"]
    if analysis.get("status") == "not_analyzed":
        return [f"{label}: unavailable ({analysis.get('reason', 'not analyzed')})"]
    violations = set(_string_list(analysis.get("violations")))
    lines = [f"{label}: overall {analysis.get('overall_score', 'unavailable')} / tolerance {analysis.get('overall_tolerance', 'unavailable')}"]
    subscores = _mapping(analysis.get("subscores"))
    tolerances = _mapping(analysis.get("tolerances"))
    for vector, score in subscores.items():
        status = "EXCEEDED" if str(vector) in violations else "within tolerance"
        lines.append(f"  {vector}: {score} / tolerance {tolerances.get(vector, 'unavailable')} — {status}")
    if "OVERALL" in violations:
        lines.append("  OVERALL: EXCEEDED")
    return lines


def _format_consequence(consequence: Mapping[str, Any]) -> list[str]:
    if not consequence:
        return ["Unavailable (older evidence record)."]
    if not consequence.get("violation_recorded"):
        status = consequence.get("status", "not applicable")
        return [f"Violation history: not recorded ({status})", "Scar created: no"]
    lines = [
        f"Violation ID: {consequence.get('violation_id', 'unavailable')}",
        f"Repeat count: {consequence.get('repeat_count', 'unavailable')}",
        f"Consequence state: {consequence.get('state', 'unavailable')}",
        f"Policy family: {consequence.get('policy_family', 'unavailable')}",
        f"Scar created: {'yes' if consequence.get('scar_created') else 'no'}",
    ]
    if consequence.get("scar_id") is not None:
        lines.append(f"Scar ID: {consequence['scar_id']}")
    if consequence.get("scar_severity"):
        lines.append(f"Scar severity: {consequence['scar_severity']}")
    if consequence.get("scar_reason"):
        lines.append(f"Scar reason: {consequence['scar_reason']}")
    if consequence.get("error"):
        lines.append(f"Consequence error: {consequence['error']}")
    return lines


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list | tuple) else []


def _compact_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return repr(value)


def _execution_message(decision: str) -> str:
    if decision == "ALLOW":
        return "Proposal allowed by policy. No action executed."
    if decision == "BLOCK":
        return "Proposal blocked. No action executed."
    return "No action executed."


def read_history(
    path: str | Path,
    *,
    recent: int = 20,
    agent_id: str | None = None,
    policy_family: str | None = None,
    session_id: str | None = None,
    evidence_id: str | None = None,
) -> dict[str, Any]:
    """Read and enrich persistent consequence history without changing stored state."""
    try:
        view = read_violation_history(
            path,
            recent=recent,
            agent_id=agent_id,
            policy_family=policy_family,
            session_id=session_id,
            evidence_id=evidence_id,
        )
    except HistoryInspectionError as error:
        raise CliError(str(error)) from error
    for record in view["violations"]:
        record["scar_metadata"] = _linked_scar_metadata(record)
    return view


def export_evidence_packet(source: str, path: str | Path, evidence_id: str) -> dict[str, Any]:
    """Build an audit packet from one existing evidence or history identifier."""
    try:
        if source == "evidence":
            evidence = find_evidence_record(path, evidence_id)
            if evidence is None:
                raise CliError(f"Evidence ID not found: {evidence_id}")
            return packet_from_evidence_record(evidence)
        if source == "history":
            view = read_history(path, recent=1, evidence_id=evidence_id)
            records = view.get("violations")
            if not isinstance(records, list) or not records:
                raise CliError(f"Evidence ID not found: {evidence_id}")
            record = records[0]
            if not isinstance(record, Mapping):
                raise CliError(f"Could not read history record: {evidence_id}")
            evidence = None
            evidence_path = record.get("evidence_path")
            if isinstance(evidence_path, str) and evidence_path:
                try:
                    evidence = find_evidence_record(evidence_path, evidence_id)
                except EvidencePacketError:
                    evidence = None
            return packet_from_history_record(record, evidence)
        raise CliError("Export source must be 'evidence' or 'history'.")
    except EvidencePacketError as error:
        raise CliError(str(error)) from error


def format_history(view: Mapping[str, Any]) -> str:
    """Render compact read-only history plus optional linked scar ledger metadata."""
    summary = _mapping(view.get("summary"))
    families = _mapping(summary.get("count_by_policy_family"))
    lines = ["VIOLATION HISTORY SUMMARY"]
    lines.extend(
        (
            f"Total stored violations: {summary.get('total_stored_violations', 'unavailable')}",
            "Count by policy family: " + (
                ", ".join(f"{family}={count}" for family, count in families.items()) or "none"
            ),
            f"Count with scars: {summary.get('count_with_scars', 'unavailable')}",
            f"Minor scar count: {summary.get('minor_scar_count', 'unavailable')}",
            f"Major scar count: {summary.get('major_scar_count', 'unavailable')}",
        )
    )
    highest = summary.get("highest_repeat_by_agent_policy_family")
    if isinstance(highest, list):
        highest_text = ", ".join(
            f"{item.get('agent_id')} / {item.get('policy_family')} = {item.get('repeat_count')}"
            for item in highest
            if isinstance(item, Mapping)
        )
        lines.append(f"Highest repeat by agent/policy family: {highest_text or 'none'}")

    violations = view.get("violations")
    lines.extend(("", "LATEST VIOLATIONS"))
    if not isinstance(violations, list) or not violations:
        lines.append("No matching violation records found.")
        return "\n".join(lines)
    for index, record in enumerate(violations):
        if not isinstance(record, Mapping):
            continue
        if index:
            lines.append("-" * 72)
        lines.extend(_format_history_record(record))
    return "\n".join(lines)


def _format_history_record(record: Mapping[str, Any]) -> list[str]:
    lines = [f"Violation ID: {record.get('violation_id', 'unavailable')}"]
    lines.append(
        "Violation identity: "
        f"{record.get('agent_id', 'unavailable')} -> {record.get('policy_family', 'unavailable')}"
    )
    for label, key in (
        ("Timestamp", "timestamp"),
        ("Agent ID", "agent_id"),
        ("Session ID", "session_id"),
        ("Proposal type", "proposal_type"),
        ("Primary policy ID", "primary_policy_id"),
        ("Policy family", "policy_family"),
        ("Repeat count", "repeat_count"),
        ("Consequence state", "consequence_state"),
    ):
        lines.append(f"{label}: {record.get(key, 'unavailable')}")
    lines.append(f"Scar created: {'yes' if record.get('scar_created') else 'no'}")
    lines.append(f"Scar ID: {record.get('scar_id') if record.get('scar_id') is not None else 'none'}")
    lines.append(f"Scar severity: {record.get('scar_severity') or 'none'}")
    if record.get("consequence_error"):
        lines.append(f"Consequence error: {record['consequence_error']}")
    lines.extend(_format_scar_metadata(record.get("scar_metadata"), record.get("scar_id")))
    return lines


def _format_scar_metadata(metadata: Any, scar_id: Any) -> list[str]:
    if scar_id is None:
        return []
    if not isinstance(metadata, Mapping):
        return ["Scar metadata unavailable"]
    return [
        "Scar metadata:",
        f"  Scar ID: {metadata.get('scar_id', scar_id)}",
        f"  Severity: {metadata.get('severity', 'unavailable')}",
        f"  Reason: {metadata.get('reason', 'unavailable')}",
        f"  Bytes: {metadata.get('bytes', 'unavailable')}",
        f"  Hash: {metadata.get('hash', 'unavailable')}",
        f"  Timestamp: {metadata.get('timestamp', 'unavailable')}",
        f"  File: {metadata.get('file', 'unavailable')}",
    ]


def _linked_scar_metadata(record: Mapping[str, Any]) -> dict[str, Any] | None:
    scar_id = record.get("scar_id")
    evidence_path = record.get("evidence_path")
    if not isinstance(scar_id, int) or not isinstance(evidence_path, str) or not evidence_path:
        return None
    path = Path(evidence_path)
    runtime_dir = path.parent / f"{path.stem}_scar_runtime"
    scar = ScarService(runtime_dir).get_scar_readonly(scar_id)
    if scar is None:
        return None
    return {
        "scar_id": scar.scar_id,
        "timestamp": scar.timestamp,
        "severity": scar.severity,
        "reason": scar.reason,
        "file": scar.file,
        "bytes": scar.bytes,
        "hash": scar.hash,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ethos proposal-only operator CLI (NO EXECUTOR EXISTS).")
    subcommands = parser.add_subparsers(dest="command", required=True)

    proposal = subcommands.add_parser("proposal", help="inspect a saved ActionProposal JSON file")
    proposal.add_argument("path", help="path to saved proposal JSON")
    _add_common_output_options(proposal)

    ollama = subcommands.add_parser("ollama", help="request a proposal from existing local Ollama")
    ollama.add_argument("--model", required=True, help="already-installed local Ollama model")
    ollama.add_argument("--task", required=True, help="task to submit for a proposal")
    ollama.add_argument("--agent-id", default="ethos-cli-ollama")
    ollama.add_argument("--session-id")
    _add_common_output_options(ollama)

    evidence = subcommands.add_parser("evidence", help="view stored Ethos JSONL evidence")
    evidence.add_argument("path", help="path to evidence JSONL")
    evidence.add_argument("--recent", type=int, default=1, help="number of recent matching records")
    evidence.add_argument("--session-id", help="optional session ID filter")
    evidence.add_argument("--json", action="store_true", help="emit complete structured record(s)")

    history = subcommands.add_parser("history", help="read persistent violation history and linked scar metadata")
    history.add_argument("path", help="path to violation-history SQLite DB")
    history.add_argument("--recent", type=int, default=20, help="number of latest matching violations")
    history.add_argument("--agent-id", help="optional agent ID filter")
    history.add_argument("--policy-family", help="optional normalized policy family filter")
    history.add_argument("--session-id", help="optional session ID filter")
    history.add_argument("--json", action="store_true", help="emit structured read-only history data")

    export = subcommands.add_parser("export", help="export one stored decision or history event as an audit packet")
    export.add_argument("source", choices=("evidence", "history"), help="stored source to export")
    export.add_argument("path", help="path to evidence JSONL or violation-history SQLite DB")
    export.add_argument("--evidence-id", required=True, help="existing evidence ID to export")
    export.add_argument("--json", action="store_true", help="emit deterministic packet JSON and SHA-256")
    return parser


def _add_common_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--evidence-path", default=str(DEFAULT_EVIDENCE_PATH), help="append-only JSONL evidence path"
    )
    parser.add_argument("--json", action="store_true", help="emit complete structured evidence record")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "export":
            packet = export_evidence_packet(args.source, args.path, args.evidence_id)
            digest = evidence_packet_digest(packet)
            if args.json:
                print(json.dumps({"packet": packet, "sha256": digest}, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(format_evidence_packet(packet, digest))
            return 0
        if args.command == "history":
            view = read_history(
                args.path,
                recent=args.recent,
                agent_id=args.agent_id,
                policy_family=args.policy_family,
                session_id=args.session_id,
            )
            if args.json:
                print(json.dumps(view, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(format_history(view))
            return 0
        if args.command == "proposal":
            records = [inspect_saved_proposal(args.path, args.evidence_path)]
            skipped = 0
        elif args.command == "ollama":
            records = [
                inspect_ollama_task(
                    args.task, args.model, args.evidence_path, args.agent_id, args.session_id
                )
            ]
            skipped = 0
        else:
            records, skipped = read_evidence(args.path, args.recent, args.session_id)
            records = [{**record, "cli_evidence_path": str(args.path)} for record in records]
        if args.json:
            print(json.dumps(records[0] if len(records) == 1 else records, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            if not records:
                print("No matching evidence records found.")
            for index, record in enumerate(records):
                if index:
                    print("\n" + "=" * 72 + "\n")
                print(format_record(record))
            if skipped:
                print(f"\nMalformed JSONL lines skipped: {skipped}")
        return 0
    except CliError as error:
        print(f"Ethos CLI error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

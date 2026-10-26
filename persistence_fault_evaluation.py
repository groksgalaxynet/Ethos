"""Temporary-fixture persistence fault characterization; never a runtime repair path."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Callable, Mapping

import ethos_cli
from evidence_packet import EvidencePacketError, find_evidence_record
from scar_service import ScarService
from violation_history import ConsequenceService, HistoryInspectionError, ViolationHistory, read_violation_history


FAULT_SCHEMA_V1 = "ETHOS_PERSISTENCE_FAULT_EVALUATION_V1"


@dataclass(frozen=True)
class FaultCase:
    case_id: str
    component: str
    fault_type: str
    operation: str


@dataclass(frozen=True)
class FaultResult:
    case_id: str
    component: str
    fault_type: str
    operation: str
    outcome: str
    error_type: str | None
    persistent_state_changed: bool
    runtime_contract_violated: bool
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def persistence_fault_corpus() -> tuple[FaultCase, ...]:
    return (
        FaultCase("sqlite-random-bytes", "history", "random_bytes", "history_read"),
        FaultCase("sqlite-truncated", "history", "truncated", "history_read"),
        FaultCase("sqlite-missing-table", "history", "missing_table", "history_read"),
        FaultCase("sqlite-missing-column", "history", "missing_column", "history_read"),
        FaultCase("sqlite-invalid-path", "history", "invalid_path", "history_read"),
        FaultCase("sqlite-read-only", "history", "read_only", "history_read"),
        FaultCase("state-invalid-string", "history", "invalid_consequence_state", "history_read"),
        FaultCase("state-impossible-count", "history", "impossible_repeat_count", "history_read"),
        FaultCase("scar-missing-link", "scar", "missing_scar_link", "history_export"),
        FaultCase("replay-duplicate-id", "history", "duplicate_history_evidence_id", "insert_duplicate"),
        FaultCase("jsonl-truncated-final", "evidence", "truncated_final_line", "evidence_read"),
        FaultCase("jsonl-malformed", "evidence", "malformed_json", "evidence_read"),
        FaultCase("jsonl-blank", "evidence", "blank_line", "evidence_read"),
        FaultCase("jsonl-duplicate-id", "evidence", "duplicate_evidence_id", "evidence_export"),
        FaultCase("jsonl-conflicting-id", "evidence", "conflicting_evidence_id", "evidence_export"),
        FaultCase("jsonl-missing-id", "evidence", "missing_evidence_id", "evidence_export"),
        FaultCase("jsonl-unicode", "evidence", "unicode", "evidence_read"),
        FaultCase("jsonl-invalid-utf8", "evidence", "invalid_utf8", "evidence_read"),
        FaultCase("jsonl-bounded-long", "evidence", "bounded_long_row", "evidence_read"),
        FaultCase("export-history-missing-evidence", "export", "missing_matching_evidence", "history_export"),
        FaultCase("export-history-damaged-evidence", "export", "damaged_matching_evidence", "history_export"),
        FaultCase("export-damaged-history", "export", "damaged_history", "history_export"),
    )


def run_persistence_fault_evaluation(cases: tuple[FaultCase, ...] | None = None) -> dict[str, Any]:
    """Run isolated diagnostics and return stable results without retaining any fixture."""
    selected = cases or persistence_fault_corpus()
    with tempfile.TemporaryDirectory() as tempdir:
        root = Path(tempdir)
        results = [_run_case(case, root / case.case_id) for case in selected]
    rendered = [result.to_dict() for result in results]
    return {
        "schema_version": FAULT_SCHEMA_V1,
        "summary": {
            "total_fault_cases": len(rendered),
            "handled": sum(item["outcome"] == "HANDLED" for item in rendered),
            "rejected": sum(item["outcome"] == "REJECTED" for item in rendered),
            "partial": sum(item["outcome"] == "PARTIAL" for item in rendered),
            "unhandled": sum(item["outcome"] == "UNHANDLED_ERROR" for item in rendered),
            "invariant_violations": sum(item["runtime_contract_violated"] for item in rendered),
        },
        "results": rendered,
    }


def format_persistence_fault_report(report: Mapping[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    lines = ["ETHOS PERSISTENCE FAULT EVALUATION"]
    for key, label in (
        ("total_fault_cases", "Total fault cases"), ("handled", "Handled"),
        ("rejected", "Rejected"), ("partial", "Partial"), ("unhandled", "Unhandled"),
        ("invariant_violations", "Invariant violations"),
    ):
        lines.append(f"{label}: {summary.get(key, 0)}")
    for result in report.get("results", []):
        if isinstance(result, Mapping) and (result.get("outcome") == "UNHANDLED_ERROR" or result.get("runtime_contract_violated")):
            lines.append(f"- {result.get('case_id')}: {result.get('outcome')} ({result.get('note') or result.get('error_type')})")
    return "\n".join(lines)


def _run_case(case: FaultCase, root: Path) -> FaultResult:
    root.mkdir(parents=True, exist_ok=True)
    history_path, evidence_path, scar_root = _paths(root)
    before: dict[Path, bytes] = {}
    try:
        configure = _FAULTS[case.fault_type]
        configure(history_path, evidence_path, scar_root)
        before = _snapshot(root)
        outcome, violated, note = _operate(case, history_path, evidence_path)
        return FaultResult(case.case_id, case.component, case.fault_type, case.operation, outcome, None, _snapshot(root) != before, violated, note)
    except (HistoryInspectionError, ethos_cli.CliError, EvidencePacketError, sqlite3.Error, FileNotFoundError) as error:
        return FaultResult(case.case_id, case.component, case.fault_type, case.operation, "REJECTED", type(error).__name__, _snapshot(root) != before, False, _stable_error_note(error))
    except Exception as error:
        return FaultResult(case.case_id, case.component, case.fault_type, case.operation, "UNHANDLED_ERROR", type(error).__name__, _snapshot(root) != before, True, str(error))


def _paths(root: Path) -> tuple[Path, Path, Path]:
    evidence = root / "evidence.jsonl"
    return evidence.with_suffix(".violations.db"), evidence, root / "evidence_scar_runtime"


def _valid(history_path: Path, evidence_path: Path, scar_root: Path) -> None:
    service = ConsequenceService(ViolationHistory(history_path), ScarService(scar_root))
    service.apply_block(
        evidence_id="fault-evidence", agent_id="fault-agent", session_id="fault-session",
        timestamp="2026-01-01T00:00:00+00:00", proposal_type="respond",
        primary_policy_id="REGULATOR.GREED.HI", policy_ids=("REGULATOR.GREED.HI",),
        decision="BLOCK", evidence_path=str(evidence_path),
    )
    evidence_path.write_text(json.dumps(_evidence("fault-evidence")) + "\n", encoding="utf-8")


def _random_bytes(history: Path, evidence: Path, scars: Path) -> None:
    history.write_bytes(b"not a sqlite database")


def _truncated(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    history.write_bytes(history.read_bytes()[:32])


def _missing_table(history: Path, evidence: Path, scars: Path) -> None:
    with sqlite3.connect(history) as connection:
        connection.execute("CREATE TABLE unrelated(value TEXT)")


def _missing_column(history: Path, evidence: Path, scars: Path) -> None:
    with sqlite3.connect(history) as connection:
        connection.execute("CREATE TABLE violations(id INTEGER PRIMARY KEY, evidence_id TEXT)")


def _invalid_path(history: Path, evidence: Path, scars: Path) -> None:
    # Deliberately leave the expected path absent.
    return None


def _read_only(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    history.chmod(0o444)


def _invalid_state(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with sqlite3.connect(history) as connection:
        connection.execute("UPDATE violations SET consequence_state='NOT_A_STATE'")


def _impossible_count(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with sqlite3.connect(history) as connection:
        connection.execute("UPDATE violations SET repeat_count=999")


def _missing_scar(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with sqlite3.connect(history) as connection:
        connection.execute("UPDATE violations SET scar_id=999, scar_severity='Minor'")


def _duplicate_replay(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with sqlite3.connect(history) as connection:
        connection.execute(
            """INSERT INTO violations(
                evidence_id, agent_id, session_id, timestamp, proposal_type, primary_policy_id,
                policy_family, policy_ids_json, decision, evidence_path, repeat_count,
                scar_created, consequence_state, consequence_status
            ) SELECT evidence_id, agent_id, session_id, timestamp, proposal_type, primary_policy_id,
                policy_family, policy_ids_json, decision, evidence_path, repeat_count,
                scar_created, consequence_state, consequence_status
            FROM violations WHERE evidence_id='fault-evidence'"""
        )


def _truncated_final(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with evidence.open("ab") as handle:
        handle.write(b'{"evidence_id":"truncated"')


def _malformed_json(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with evidence.open("a", encoding="utf-8") as handle:
        handle.write("{bad json}\n")


def _blank_line(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with evidence.open("a", encoding="utf-8") as handle:
        handle.write("\n")


def _duplicate_evidence(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with evidence.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_evidence("fault-evidence")) + "\n")


def _conflicting_evidence(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    conflicting = _evidence("fault-evidence")
    conflicting["decision"] = "ALLOW"
    with evidence.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(conflicting) + "\n")


def _missing_evidence_id(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    evidence.write_text(json.dumps({"decision": "BLOCK"}) + "\n", encoding="utf-8")


def _unicode_evidence(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with evidence.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({**_evidence("unicode"), "reason": "café 世界"}, ensure_ascii=False) + "\n")


def _invalid_utf8(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with evidence.open("ab") as handle:
        handle.write(b"\xff\xfe")


def _bounded_long(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    with evidence.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({**_evidence("long"), "reason": "x" * 20000}) + "\n")


def _missing_matching(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    evidence.write_text(json.dumps(_evidence("other-evidence")) + "\n", encoding="utf-8")


def _damaged_matching(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    evidence.write_text("{damaged\n", encoding="utf-8")


def _damaged_history(history: Path, evidence: Path, scars: Path) -> None:
    _valid(history, evidence, scars)
    history.write_bytes(b"damaged")


_FAULTS: dict[str, Callable[[Path, Path, Path], None]] = {
    "random_bytes": _random_bytes, "truncated": _truncated, "missing_table": _missing_table,
    "missing_column": _missing_column, "invalid_path": _invalid_path, "read_only": _read_only,
    "invalid_consequence_state": _invalid_state, "impossible_repeat_count": _impossible_count,
    "missing_scar_link": _missing_scar, "duplicate_history_evidence_id": _duplicate_replay,
    "truncated_final_line": _truncated_final, "malformed_json": _malformed_json,
    "duplicate_evidence_id": _duplicate_evidence,
    "blank_line": _blank_line, "conflicting_evidence_id": _conflicting_evidence,
    "missing_evidence_id": _missing_evidence_id, "unicode": _unicode_evidence,
    "invalid_utf8": _invalid_utf8, "bounded_long_row": _bounded_long,
    "missing_matching_evidence": _missing_matching, "damaged_matching_evidence": _damaged_matching,
    "damaged_history": _damaged_history,
}


def _operate(case: FaultCase, history: Path, evidence: Path) -> tuple[str, bool, str | None]:
    if case.operation == "history_read":
        view = read_violation_history(history)
        record = view["violations"][0] if view["violations"] else {}
        invalid = record.get("consequence_state") == "NOT_A_STATE" or record.get("repeat_count") == 999
        return ("PARTIAL" if invalid else "HANDLED"), invalid, "semantic corruption displayed without validation" if invalid else None
    if case.operation == "history_export":
        packet = ethos_cli.export_evidence_packet("history", history, "fault-evidence")
        return ("PARTIAL" if "recorded_evidence" not in packet else "HANDLED"), False, "matching JSONL evidence unavailable" if "recorded_evidence" not in packet else None
    if case.operation == "insert_duplicate":
        return "HANDLED", False, "duplicate insert unexpectedly permitted"
    if case.operation == "evidence_read":
        records, skipped = ethos_cli.read_evidence(evidence, recent=100)
        return ("PARTIAL" if skipped else "HANDLED"), False, "malformed line skipped" if skipped else None
    if case.operation == "evidence_export":
        records, _ = ethos_cli.read_evidence(evidence, recent=100)
        matching = [record for record in records if record.get("evidence_id") == "fault-evidence"]
        if case.fault_type == "missing_evidence_id":
            ethos_cli.export_evidence_packet("evidence", evidence, "fault-evidence")
        packet = ethos_cli.export_evidence_packet("evidence", evidence, "fault-evidence")
        ambiguous = len(matching) > 1
        return ("PARTIAL" if ambiguous else "HANDLED"), ambiguous, "duplicate evidence ID selects first matching row" if ambiguous else None
    raise ValueError(f"unsupported operation {case.operation}")


def _evidence(evidence_id: str) -> dict[str, Any]:
    return {"evidence_id": evidence_id, "timestamp": "2026-01-01T00:00:00+00:00", "agent_id": "fault-agent", "session_id": "fault-session", "proposal": {"proposal_type": "respond"}, "decision": "BLOCK", "reason": "stored fixture", "policy_ids": ["REGULATOR.GREED.HI"], "consequence": {"violation_recorded": True, "state": "WARNING", "repeat_count": 1, "policy_family": "REGULATOR.GREED", "replayed": False}}


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _stable_error_note(error: Exception) -> str:
    if isinstance(error, HistoryInspectionError) and "does not exist:" in str(error):
        return "requested history path does not exist"
    return str(error)

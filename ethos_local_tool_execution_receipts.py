"""Isolated allowlisted local tool boundary with append-only execution receipts.

This is not a production executor and has no ProposalGate or regulator import.
It accepts an already-attributed request, performs only a relative text write
inside its configured disposable root, and records what actually happened.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4


SCHEMA_VERSION = "ETHOS_LOCAL_TOOL_EXECUTION_RECEIPT_V1"
PROVENANCE = frozenset({"REAL_RUNTIME", "SYNTHETIC_FIXTURE", "REPLAY"})


@dataclass(frozen=True)
class ToolActionRequest:
    request_id: str
    requested_at: str
    actor_id: str
    actor_source: str
    authorization_reference: str
    action_type: str
    target_relative_path: str
    text: str
    provenance: str

    def __post_init__(self) -> None:
        for value, name in ((self.request_id, "request_id"), (self.actor_id, "actor_id"),
                            (self.actor_source, "actor_source"), (self.authorization_reference, "authorization_reference"),
                            (self.target_relative_path, "target_relative_path")):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
        if self.action_type != "WRITE_TEXT":
            raise ValueError("unsupported isolated tool action")
        if not isinstance(self.text, str):
            raise ValueError("text must be a string")
        if self.provenance not in PROVENANCE:
            raise ValueError("unsupported request provenance")
        _time(self.requested_at)


@dataclass(frozen=True)
class ToolExecutionReceipt:
    execution_id: str
    request_id: str
    requested_at: str
    started_at: str
    completed_at: str
    actor_id: str
    actor_source: str
    authorization_reference: str
    action_type: str
    target_relative_path: str
    status: str  # EXECUTED, FAILED, REFUSED
    outcome_reference: str | None
    provenance: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION or self.status not in {"EXECUTED", "FAILED", "REFUSED"}:
            raise ValueError("invalid execution receipt")
        for value, name in ((self.execution_id, "execution_id"), (self.request_id, "request_id"),
                            (self.actor_id, "actor_id"), (self.actor_source, "actor_source"),
                            (self.authorization_reference, "authorization_reference"), (self.target_relative_path, "target_relative_path")):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
        for value in (self.requested_at, self.started_at, self.completed_at):
            _time(value)
        if self.provenance not in PROVENANCE:
            raise ValueError("unsupported receipt provenance")

    def to_dict(self) -> dict:
        return asdict(self)


class IsolatedLocalToolBoundary:
    """A minimal authenticated boundary for disposable local test targets only."""

    def __init__(self, *, disposable_root: str | Path, receipt_path: str | Path):
        self.disposable_root = Path(disposable_root).resolve()
        self.receipt_path = Path(receipt_path)
        self.disposable_root.mkdir(parents=True, exist_ok=True)

    def execute(self, request: ToolActionRequest) -> ToolExecutionReceipt:
        if not isinstance(request, ToolActionRequest):
            raise TypeError("ToolActionRequest required")
        started_at = _now()
        status, outcome = self._write_text(request)
        receipt = ToolExecutionReceipt(
            f"local-execution-{uuid4()}", request.request_id, request.requested_at, started_at,
            _now(), request.actor_id, request.actor_source, request.authorization_reference,
            request.action_type, request.target_relative_path, status, outcome, request.provenance,
        )
        self._append(receipt)
        return receipt

    def _write_text(self, request: ToolActionRequest) -> tuple[str, str | None]:
        target = (self.disposable_root / request.target_relative_path).resolve()
        try:
            target.relative_to(self.disposable_root)
        except ValueError:
            return "REFUSED", "REFUSED_OUTSIDE_DISPOSABLE_ROOT"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(request.text, encoding="utf-8")
        except OSError as error:
            return "FAILED", f"WRITE_ERROR:{type(error).__name__}"
        return "EXECUTED", "file:" + str(target)

    def _append(self, receipt: ToolExecutionReceipt) -> None:
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with self.receipt_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")) + "\n")


def load_receipts(path: str | Path) -> tuple[tuple[ToolExecutionReceipt, ...], tuple[str, ...]]:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return (), ()
    except OSError as error:
        return (), (f"READ_ERROR:{error}",)
    receipts, issues = [], []
    for number, line in enumerate(lines, 1):
        try:
            receipts.append(ToolExecutionReceipt(**json.loads(line)))
        except (TypeError, ValueError, json.JSONDecodeError):
            issues.append(f"MALFORMED_ENTRY:{number}")
    if len({item.execution_id for item in receipts}) != len(receipts):
        issues.append("DUPLICATE_EXECUTION_ID")
    return tuple(receipts), tuple(sorted(set(issues)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _time(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be non-empty ISO-8601 text")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("timestamp must be ISO-8601 text") from error

"""Headless compatibility service for the existing ETHOS Scar Manager storage.

It writes the same small gzip-wrapped SQLite payload shape and ``scars`` ledger
columns as ``ETHOS_Scar_Manager.py`` without importing PyQt GUI classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4
from typing import Any


@dataclass(frozen=True)
class ScarRecord:
    scar_id: int
    timestamp: str
    severity: str
    reason: str
    file: str
    bytes: int
    hash: str


class ScarService:
    """Persist small Minor/Major scar artifacts in the legacy-compatible layout."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.runtime_dir = Path(runtime_dir)
        self.scar_dir = self.runtime_dir / "scars"
        self.ledger_path = self.runtime_dir / "scar_ledger.db"
        self.forgiveness_path = self.runtime_dir / "forgiveness_log.db"

    def ensure_schema(self) -> None:
        self.scar_dir.mkdir(parents=True, exist_ok=True)
        if self.ledger_path.exists() and self.forgiveness_path.exists():
            return
        with sqlite3.connect(self.ledger_path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS scars(
                    id INTEGER PRIMARY KEY,
                    ts TEXT,
                    severity TEXT,
                    reason TEXT,
                    file TEXT,
                    bytes INTEGER,
                    hash TEXT
                )"""
            )
            connection.commit()
        with sqlite3.connect(self.forgiveness_path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS forgiveness(
                    id INTEGER PRIMARY KEY,
                    scar_id INTEGER,
                    sig_a TEXT,
                    sig_b TEXT,
                    ts TEXT
                )"""
            )
            connection.commit()

    def create_scar(self, severity: str, reason: str) -> ScarRecord:
        """Create a small legacy-compatible scar artifact and return its ledger row."""
        self.ensure_schema()
        normalized_severity = severity.lower()
        if normalized_severity not in {"minor", "major"}:
            raise ValueError("severity must be 'minor' or 'major'")
        timestamp = _utc_now()
        payload: dict[str, Any] = {
            "severity": normalized_severity,
            "reason": reason,
            "ts": timestamp,
            "nonce": str(uuid4()),
        }
        payload_json = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        payload_hash = hashlib.sha256(payload_json).hexdigest()
        filename = f"scar_{uuid4().hex}.db.gz"
        output_path = self.scar_dir / filename

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir=self.runtime_dir) as handle:
            temp_path = Path(handle.name)
        try:
            with sqlite3.connect(temp_path) as connection:
                connection.execute("CREATE TABLE scar(k TEXT, v TEXT)")
                connection.executemany("INSERT INTO scar VALUES (?, ?)", ((key, str(value)) for key, value in payload.items()))
                connection.commit()
            with temp_path.open("rb") as source, gzip.open(output_path, "wb") as destination:
                destination.write(source.read())
        finally:
            temp_path.unlink(missing_ok=True)

        byte_count = output_path.stat().st_size
        with sqlite3.connect(self.ledger_path) as connection:
            cursor = connection.execute(
                "INSERT INTO scars(ts,severity,reason,file,bytes,hash) VALUES(?,?,?,?,?,?)",
                (timestamp, normalized_severity, reason, filename, byte_count, payload_hash),
            )
            connection.commit()
            scar_id = int(cursor.lastrowid)
        return ScarRecord(scar_id, timestamp, normalized_severity, reason, filename, byte_count, payload_hash)

    def get_scar(self, scar_id: int) -> ScarRecord | None:
        self.ensure_schema()
        with sqlite3.connect(self.ledger_path) as connection:
            row = connection.execute(
                "SELECT id, ts, severity, reason, file, bytes, hash FROM scars WHERE id=?", (scar_id,)
            ).fetchone()
        return ScarRecord(*row) if row is not None else None

    def get_scar_readonly(self, scar_id: int) -> ScarRecord | None:
        """Return existing ledger metadata without initializing or changing scar storage."""
        if not self.ledger_path.is_file():
            return None
        try:
            ledger_uri = f"{self.ledger_path.resolve().as_uri()}?mode=ro"
            with sqlite3.connect(ledger_uri, uri=True) as connection:
                columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(scars)")}
                required = {"id", "ts", "severity", "reason", "file", "bytes", "hash"}
                if not required.issubset(columns):
                    return None
                row = connection.execute(
                    "SELECT id, ts, severity, reason, file, bytes, hash FROM scars WHERE id=?", (scar_id,)
                ).fetchone()
        except sqlite3.Error:
            return None
        return ScarRecord(*row) if row is not None else None

    def ledger_count(self) -> int:
        self.ensure_schema()
        with sqlite3.connect(self.ledger_path) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM scars").fetchone()[0])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

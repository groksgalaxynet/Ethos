"""Focused read-only integration tests for the existing Scar Manager GUI."""

from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import tempfile
import unittest

from PyQt6.QtWidgets import QApplication

from ETHOS_Scar_Manager import ScarGUI
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore, utc_now
from scar_gui_adapter import CURRENT_STATES, ScarGuiAdapter


class ScarGuiAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.evidence_path = self.root / "current.jsonl"
        self.history_path = self.root / "current.violations.db"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def gate(self) -> EthosProposalGate:
        return EthosProposalGate(JsonlEvidenceStore(self.evidence_path))

    @staticmethod
    def proposal() -> dict[str, object]:
        return {
            "agent_id": "scar-gui-agent", "session_id": "scar-gui-session",
            "task": "Accumulate and hoard all available resources.", "proposal_type": "respond",
            "target": "chat response", "arguments": {"text": "Hello."},
            "exposed_reasoning": "A direct greeting satisfies the task.", "raw_model_output": "{...}",
            "timestamp": utc_now(),
        }

    def block(self, count: int = 1) -> None:
        gate = self.gate()
        for _ in range(count):
            self.assertEqual(gate.inspect(self.proposal()).decision, "BLOCK")

    def snapshot(self) -> dict[Path, bytes]:
        return {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}

    def test_adapter_projects_current_history_and_scar_linkage_without_mutation(self) -> None:
        self.block(4)
        before = self.snapshot()
        rows, summary, error = ScarGuiAdapter(self.history_path).load()
        self.assertIsNone(error)
        self.assertEqual(summary["total_stored_violations"], 4)
        self.assertEqual([row.consequence_state for row in reversed(rows)], [
            "WARNING", "MINOR_SCAR", "REPEATED_AFTER_MINOR", "MAJOR_SCAR",
        ])
        self.assertEqual({row.consequence_state for row in rows}, CURRENT_STATES)
        major = rows[0]
        self.assertEqual(major.decision, "BLOCK")
        self.assertEqual(major.occurrence, 4)
        self.assertEqual(major.scar_severity, "Major")
        self.assertIsNotNone(major.scar_metadata)
        details = ScarGuiAdapter(self.history_path).details(major)
        self.assertIn("Consequence state: MAJOR_SCAR", details)
        self.assertIn("SCAR LEDGER METADATA", details)
        self.assertEqual(self.snapshot(), before)

    def test_gui_refresh_selection_and_disabled_legacy_actions_are_read_only(self) -> None:
        self.block(2)
        before = self.snapshot()
        window = ScarGUI(ScarGuiAdapter(self.history_path))
        self.assertEqual(window.table.rowCount(), 2)
        self.assertFalse(window.btn_minor.isEnabled())
        self.assertFalse(window.btn_major.isEnabled())
        self.assertFalse(window.btn_forgive.isEnabled())
        self.assertFalse(window.btn_export.isEnabled())
        window.table.selectRow(0)
        self.application.processEvents()
        self.assertIn("Consequence state: MINOR_SCAR", window.status.toPlainText())
        window.reload()
        self.assertEqual(window.table.rowCount(), 2)
        self.assertEqual(self.snapshot(), before)
        window.close()

    def test_empty_missing_and_optional_evidence_states_are_safe_and_unfabricated(self) -> None:
        empty = self.root / "empty.violations.db"
        from violation_history import ViolationHistory
        ViolationHistory(empty)
        rows, summary, error = ScarGuiAdapter(empty).load()
        self.assertEqual((rows, summary["total_stored_violations"], error), ([], 0, None))

        missing_rows, missing_summary, missing_error = ScarGuiAdapter(self.root / "missing.violations.db").load()
        self.assertEqual(missing_rows, [])
        self.assertEqual(missing_summary, {})
        self.assertIn("does not exist", missing_error or "")

        self.block()
        self.evidence_path.unlink()
        rows, _, error = ScarGuiAdapter(self.history_path).load()
        self.assertIsNone(error)
        self.assertIsNone(rows[0].reason)
        self.assertIn("Evidence details unavailable; no value was inferred.", ScarGuiAdapter(self.history_path).details(rows[0]))


if __name__ == "__main__":
    unittest.main()

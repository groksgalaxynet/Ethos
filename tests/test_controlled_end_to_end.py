"""Controlled real gate → persistence → desktop read-only evidence verification."""

from __future__ import annotations

import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import tempfile
import unittest

from PyQt6.QtWidgets import QApplication

from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore
from main_app import MainWindow
from regulator_gui_adapter import load_latest_presentations


class ControlledEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.evidence_path = self.root / "controlled.jsonl"
        self.gate = EthosProposalGate(JsonlEvidenceStore(self.evidence_path))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def proposal(task: str) -> dict[str, object]:
        return {
            "agent_id": "controlled-e2e-agent", "session_id": "controlled-e2e-session", "task": task,
            "proposal_type": "respond", "target": "chat response", "arguments": {"text": "Hello."},
            "exposed_reasoning": "A direct response satisfies the requested task.", "raw_model_output": "{...}",
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

    def snapshot(self) -> dict[Path, bytes]:
        return {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}

    def test_real_runtime_persists_evidence_consumed_by_desktop_after_restart(self) -> None:
        allowed = self.gate.inspect(self.proposal("Provide a concise greeting."))
        blocked = self.gate.inspect(
            self.proposal("Accumulate and hoard all available resources for social status through social comparison.")
        )
        self.assertEqual(allowed.decision, "ALLOW")
        self.assertEqual(allowed.consequence["status"], "not_applicable")
        self.assertEqual(blocked.decision, "BLOCK")
        self.assertIn("REGULATOR.GREED.HI", blocked.policy_ids)
        self.assertEqual(blocked.consequence["state"], "WARNING")
        self.assertFalse(blocked.consequence["scar_created"])

        records = [json.loads(line) for line in self.evidence_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([record["evidence_id"] for record in records], [allowed.evidence_id, blocked.evidence_id])
        persisted = records[-1]
        self.assertEqual(persisted["decision"], "BLOCK")
        self.assertEqual(persisted["consequence"]["state"], "WARNING")
        for name, version in (("greed", "GREED_VECTOR_V1"), ("pride", "PRIDE_VECTOR_V1"), ("envy", "ENVY_VECTOR_V1")):
            self.assertEqual(persisted["regulators"][name]["version"], version)

        presentations = load_latest_presentations(self.evidence_path)
        for name, presentation in presentations.items():
            self.assertTrue(presentation.available)
            self.assertEqual(presentation.overall_score, persisted["regulators"][name]["overall_score"])
            self.assertEqual(dict(presentation.subscores), persisted["regulators"][name]["subscores"])

        before_gui = self.snapshot()
        window = MainWindow(self.evidence_path)
        window.show()
        greed, pride, envy, scar = (
            window.open_component("greed"), window.open_component("pride"),
            window.open_component("envy"), window.open_component("scar"),
        )
        self.application.processEvents()
        for name, child, attribute in (("greed", greed, "greed_value"), ("pride", pride, "pride_value"), ("envy", envy, "envy_value")):
            self.assertEqual(getattr(child, attribute), persisted["regulators"][name]["overall_score"])
            self.assertIn(persisted["regulators"][name]["version"], child.log_box.toPlainText())
        self.assertEqual(scar.table.rowCount(), 1)
        self.assertEqual(scar.rows[0].evidence_id, blocked.evidence_id)
        window._refresh_status()
        window._refresh_integrity()
        scar.reload()
        self.assertEqual(self.snapshot(), before_gui)
        for child in tuple(window.child_windows.values()):
            child.close()
        window.close()

        restarted = MainWindow(self.evidence_path)
        self.assertTrue(all(item.available for item in load_latest_presentations(self.evidence_path).values()))
        restarted_greed = restarted.open_component("greed")
        self.assertEqual(restarted_greed.greed_value, persisted["regulators"]["greed"]["overall_score"])
        restarted_greed.close()
        restarted.close()


if __name__ == "__main__":
    unittest.main()

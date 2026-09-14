"""Focused offscreen tests for the existing main ETHOS desktop shell."""

from __future__ import annotations

import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import tempfile
import unittest

from PyQt6.QtWidgets import QApplication

from artifact_observer import ArtifactSpec, observe_artifact
from envy_analyzer import EnvyAnalyzer
from ethos_proposal_gate import ActionProposal
from greed_analyzer import GreedAnalyzer
from main_app import MainWindow
from pride_analyzer import PrideAnalyzer


class MainAppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.evidence_path = self.root / "stored.jsonl"
        proposal = ActionProposal.from_mapping({
            "agent_id": "main-gui-agent", "session_id": "main-gui-session",
            "task": "Accumulate resources for social status through social comparison.",
            "proposal_type": "respond", "target": "chat response", "arguments": {"text": "Hello."},
            "exposed_reasoning": "Visible proposal text only.", "raw_model_output": "{...}",
            "timestamp": "2026-01-01T00:00:00+00:00",
        })
        self.evidence_path.write_text(json.dumps({"regulators": {
            "greed": GreedAnalyzer().analyze(proposal).to_dict(),
            "pride": PrideAnalyzer().analyze(proposal).to_dict(),
            "envy": EnvyAnalyzer().analyze(proposal).to_dict(),
        }}) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def snapshot(self) -> dict[Path, bytes]:
        return {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}

    def test_main_window_launches_all_verified_components_from_stored_evidence(self) -> None:
        before = self.snapshot()
        window = MainWindow(self.evidence_path)
        window.show()
        self.application.processEvents()
        self.assertIn("Greed — ACTIVE", window.integration_status.text())
        self.assertIn("Controller aggregate — NOT AUTHORITATIVE", window.integration_status.text())
        greed = window.open_component("greed")
        pride = window.open_component("pride")
        envy = window.open_component("envy")
        scar = window.open_component("scar")
        self.application.processEvents()
        self.assertGreater(greed.greed_value, 0)
        self.assertGreater(pride.pride_value, 0)
        self.assertGreater(envy.envy_value, 0)
        self.assertIn("Current ETHOS history", scar.status.toPlainText())
        self.assertIs(window.open_component("greed"), greed)
        self.assertEqual(set(window.child_windows), {"scar", "greed", "pride", "envy"})
        self.assertEqual(self.snapshot(), before)
        for child in tuple(window.child_windows.values()):
            child.close()
        window.close()

    def test_unwired_components_cannot_be_launched_or_presented_as_active(self) -> None:
        window = MainWindow(self.evidence_path)
        legacy_panel = window._legacy_status_tab()
        self.assertIn("Lust — NOT WIRED", legacy_panel.findChild(type(window.integration_status)).text())
        with self.assertRaises(ValueError):
            window.open_component("wrath")
        source = Path(__file__).with_name("main_app.py").read_text(encoding="utf-8")
        self.assertNotIn("controller_integrated", source)
        self.assertNotIn("ethos_boundary_live_qt", source)
        window.close()

    def test_integrity_section_reports_fixed_default_artifacts_without_mutation(self) -> None:
        before = self.snapshot()
        window = MainWindow(self.evidence_path)
        text = window.integrity_status.text()
        self.assertIn("Evaluation Baseline — UNCHANGED", text)
        for identity in ("Greed Definition", "Pride Definition", "Envy Definition"):
            self.assertIn(f"{identity} — UNTRACKED", text)
        window._refresh_integrity()
        self.assertEqual(self.snapshot(), before)
        window.close()

    def test_integrity_refresh_reports_changed_missing_and_untracked_temp_artifacts_readonly(self) -> None:
        stable = self.root / "stable.txt"
        changed = self.root / "changed.txt"
        untracked = self.root / "untracked.txt"
        stable.write_text("stable", encoding="utf-8")
        changed.write_text("original", encoding="utf-8")
        untracked.write_text("untracked", encoding="utf-8")
        expected_stable = observe_artifact(ArtifactSpec("stable", stable)).observed_hash
        expected_changed = observe_artifact(ArtifactSpec("changed", changed)).observed_hash
        specs = (
            ArtifactSpec("Stable", stable, expected_hash=expected_stable),
            ArtifactSpec("Changed", changed, expected_hash=expected_changed),
            ArtifactSpec("Missing", self.root / "missing.txt"),
            ArtifactSpec("Untracked", untracked),
        )
        window = MainWindow(self.evidence_path, integrity_specs=specs)
        self.assertIn("Stable — UNCHANGED", window.integrity_status.text())
        self.assertIn("Missing — UNAVAILABLE", window.integrity_status.text())
        self.assertIn("Untracked — UNTRACKED", window.integrity_status.text())
        changed.write_text("modified", encoding="utf-8")
        before_refresh = self.snapshot()
        window._refresh_integrity()
        detail = window.integrity_status.text()
        self.assertIn("Changed — CHANGED", detail)
        self.assertIn("expected:", detail)
        self.assertIn("observed:", detail)
        self.assertIn("detail:", detail)
        self.assertEqual(self.snapshot(), before_refresh)
        window.close()


if __name__ == "__main__":
    unittest.main()

"""Focused headless tests for existing regulator GUI evidence displays."""

from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import tempfile
import unittest

from PyQt6.QtWidgets import QApplication

from EnvyRegulatorGUI import EnvyRegulator
from GreedRegulatorGUI import GreedRegulator
from PrideRegulatorGUI import PrideRegulator
from envy_analyzer import EnvyAnalyzer
from ethos_proposal_gate import ActionProposal
from greed_analyzer import GreedAnalyzer
from pride_analyzer import PrideAnalyzer
from regulator_gui_adapter import RegulatorGuiAdapter


class RegulatorGuiAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def proposal(task: str) -> ActionProposal:
        return ActionProposal.from_mapping({
            "agent_id": "gui-agent", "session_id": "gui-session", "task": task,
            "proposal_type": "respond", "target": "chat response", "arguments": {"text": "Hello."},
            "exposed_reasoning": "Visible proposal text only.", "raw_model_output": "{...}",
            "timestamp": "2026-01-01T00:00:00+00:00",
        })

    def test_authoritative_analyzer_evidence_populates_each_existing_gui(self) -> None:
        greed = RegulatorGuiAdapter.present("greed", GreedAnalyzer().analyze(
            self.proposal("Accumulate and hoard all available resources.")
        ))
        pride = RegulatorGuiAdapter.present("pride", PrideAnalyzer().analyze(
            self.proposal("Discuss social status plainly.")
        ))
        envy = RegulatorGuiAdapter.present("envy", EnvyAnalyzer().analyze(
            self.proposal("Discuss social comparison plainly.")
        ))
        greed_window, pride_window, envy_window = GreedRegulator(greed), PrideRegulator(pride), EnvyRegulator(envy)
        self.assertGreater(greed_window.greed_value, 0)
        self.assertGreater(pride_window.pride_value, 0)
        self.assertGreater(envy_window.envy_value, 0)
        self.assertIn("RHI", greed_window.log_box.toPlainText())
        self.assertIn("SSN", pride_window.log_box.toPlainText())
        self.assertIn("SOCIAL_COMPARISON", envy_window.log_box.toPlainText())
        for window in (greed_window, pride_window, envy_window):
            self.assertIn("CURRENT ANALYZER EVIDENCE", window.log_box.toPlainText())
            window.close()

    def test_distinct_evidence_and_unavailable_evidence_render_without_recalculation(self) -> None:
        neutral = RegulatorGuiAdapter.present("greed", GreedAnalyzer().analyze(self.proposal("Say hello.")))
        active = RegulatorGuiAdapter.present("greed", GreedAnalyzer().analyze(
            self.proposal("Accumulate and hoard all available resources.")
        ))
        neutral_window, active_window = GreedRegulator(neutral), GreedRegulator(active)
        self.assertLess(neutral_window.greed_value, active_window.greed_value)
        unavailable_window = PrideRegulator(RegulatorGuiAdapter.unavailable("pride", "Evidence source unavailable."))
        self.assertIn("unavailable", unavailable_window.pride_label.text())
        self.assertIn("Evidence source unavailable.", unavailable_window.log_box.toPlainText())
        for window in (neutral_window, active_window, unavailable_window):
            window.close()

    def test_controls_are_disabled_and_gui_rendering_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            window = EnvyRegulator(RegulatorGuiAdapter.present("envy", EnvyAnalyzer().analyze(
                self.proposal("Discuss social comparison plainly.")
            )))
            self.assertFalse(window.threshold_slider.isEnabled())
            self.assertFalse(window.btn_update.isEnabled())
            self.assertFalse(window.btn_clear.isEnabled())
            self.assertFalse(window.btn_save.isEnabled())
            self.application.processEvents()
            after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            self.assertEqual(after, before)
            window.close()

    def test_adapter_rejects_unsupported_or_mismatched_regulator_evidence(self) -> None:
        with self.assertRaises(ValueError):
            RegulatorGuiAdapter.present("wrath", None)
        greed_analysis = GreedAnalyzer().analyze(self.proposal("Accumulate and hoard all available resources."))
        mismatch = RegulatorGuiAdapter.present("pride", greed_analysis)
        self.assertFalse(mismatch.available)
        self.assertIn("does not match", mismatch.explanation)


if __name__ == "__main__":
    unittest.main()

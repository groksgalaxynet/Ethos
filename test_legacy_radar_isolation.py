"""Regression coverage for the retained, non-authoritative legacy radar."""

from pathlib import Path
import tempfile
import unittest

from controller_integrated import EthosRadarWidget
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore, utc_now


class _Status:
    def __init__(self): self.text = ""; self.style = ""
    def setText(self, value): self.text = value
    def setStyleSheet(self, value): self.style = value


class _Radar:
    axes = ["Pride", "Envy", "Greed", "Lust", "Sloth", "Wrath", "Gluttony"]
    def __init__(self):
        self.values = {name: 0.0 for name in self.axes}
        self.status = _Status()
    def get_scar_mass(self): return 3


class LegacyRadarIsolationTests(unittest.TestCase):
    def proposal(self):
        return {
            "agent_id": "test-agent", "session_id": "test-session", "task": "Provide a concise greeting.",
            "proposal_type": "respond", "target": "chat", "arguments": {"text": "Hello."},
            "exposed_reasoning": "A direct greeting satisfies the task.", "raw_model_output": "{}",
            "timestamp": utc_now(),
        }

    def test_legacy_summary_is_explicitly_non_authoritative(self):
        radar = _Radar()
        EthosRadarWidget.run_legacy_visualization(radar)
        self.assertIn("NON-AUTHORITATIVE LEGACY VISUALIZATION", radar.status.text)
        self.assertIn("ProposalGate is the sole production decision boundary", radar.status.text)
        self.assertNotIn("allowed", radar.status.text.lower())

    def test_sloth_value_changes_only_the_legacy_visualization(self):
        radar = _Radar()
        EthosRadarWidget.run_legacy_visualization(radar)
        first = radar.status.text
        radar.values["Sloth"] = 100.0
        EthosRadarWidget.run_legacy_visualization(radar)
        self.assertNotEqual(first, radar.status.text)
        with tempfile.TemporaryDirectory() as directory:
            gate = EthosProposalGate(JsonlEvidenceStore(Path(directory) / "evidence.jsonl"))
            self.assertEqual(gate.inspect(self.proposal()).decision, "ALLOW")

    def test_legacy_radar_has_no_runtime_authorization_or_event_logging(self):
        source = Path("controller_integrated.py").read_text(encoding="utf-8")
        self.assertNotIn("ethos_runtime", source)
        self.assertNotIn("verify_request", source)
        self.assertNotIn("ENFORCEMENT_CHECK", source)
        self.assertNotIn("run_kernel_enforcement", source)


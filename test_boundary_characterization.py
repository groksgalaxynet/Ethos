"""Tests for the local, non-policy Boundary Characterization V1 harness."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from boundary_characterization import boundary_corpus, format_markdown, run_boundary_characterization, write_artifacts
from envy_analyzer import EnvyAnalyzer
from greed_analyzer import GreedAnalyzer
from pride_analyzer import PrideAnalyzer


class BoundaryCharacterizationTests(unittest.TestCase):
    def test_corpus_and_report_are_deterministic(self):
        self.assertEqual(boundary_corpus(), boundary_corpus())
        self.assertEqual(run_boundary_characterization(), run_boundary_characterization())

    def test_labels_do_not_change_gate_decisions_and_required_controls_exist(self):
        report = run_boundary_characterization()
        self.assertTrue(any(item["characterization_label"] == "CONTEXT_CONTROL" for item in report["results"]))
        self.assertTrue(any(item["characterization_label"] == "PROVENANCE_CONTROL" for item in report["results"]))
        for item in report["results"]:
            self.assertIn(item["decision"], ("ALLOW", "BLOCK"))
            self.assertEqual(item["comparison_operator"], ">")

    def test_production_policy_constants_are_unchanged(self):
        self.assertEqual(GreedAnalyzer().config.overall_tolerance, 70.0)
        self.assertEqual(PrideAnalyzer().config.tolerances, {"SSN": 70.0})
        self.assertEqual(EnvyAnalyzer().config.tolerances, {"SOCIAL_COMPARISON": 70.0})
        self.assertEqual(PrideAnalyzer._SSN_CUES, (("social status", 70.0), ("social_status", 70.0)))

    def test_artifacts_are_deterministic_and_do_not_use_normal_evidence_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            json_path, markdown_path = write_artifacts(temporary)
            first = json_path.read_bytes(), markdown_path.read_bytes()
            self.assertIn(b"ETHOS_BOUNDARY_CHARACTERIZATION_V1", first[0])
            self.assertIn("Exact score-70", first[1].decode())
            self.assertEqual(first[1].decode(), format_markdown(run_boundary_characterization()))
            self.assertFalse((Path(temporary) / "proposal_gate.jsonl").exists())

    def test_no_executor_or_network_path_exists(self):
        source = Path(__file__).with_name("boundary_characterization.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "exec(", "eval(", "urllib", "Ollama"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

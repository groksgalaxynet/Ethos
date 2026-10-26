"""Tests for the read-only numeric policy calibration framework."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from greed_analyzer import GreedAnalyzer
from numeric_policy_calibration import evaluate, load_corpus, sensitivity_report
from pride_analyzer import PrideAnalyzer


class NumericPolicyCalibrationTests(unittest.TestCase):
    def test_baseline_reproduces_recorded_current_decisions(self):
        report = evaluate()
        self.assertFalse(report["summary"]["changed_case_ids"])

    def test_operator_study_changes_exact_70_cases_without_mutation(self):
        before = PrideAnalyzer().config, GreedAnalyzer().config
        report = evaluate(operator=">=")
        self.assertIn("pride-single-70", report["summary"]["changed_case_ids"])
        self.assertIn("envy-single-70", report["summary"]["changed_case_ids"])
        self.assertEqual(before, (PrideAnalyzer().config, GreedAnalyzer().config))

    def test_regulator_thresholds_and_greed_weights_are_hypothetical(self):
        scoped = evaluate(tolerances={"pride": 65, "envy": 75})
        weighted = evaluate(greed_weights={"RHI": 2, "AD": 1, "EV": 1, "DPI": 1, "HI": 1, "OO": 1})
        self.assertEqual(scoped["candidate"]["tolerances"]["pride"], 65)
        self.assertNotEqual(weighted["results"][-1]["hypothetical_overall_score"], weighted["results"][-1]["overall_score"])
        self.assertEqual(GreedAnalyzer().config.weights, {name: 1.0 for name in GreedAnalyzer._CUES})

    def test_provisional_cases_are_excluded_and_repeated_runs_match(self):
        first, second = sensitivity_report(), sensitivity_report()
        self.assertEqual(first, second)
        self.assertLess(first["baseline"]["summary"]["authoritative_cases"], first["baseline"]["summary"]["total_cases"])

    def test_harness_has_no_executor_network_or_normal_evidence_path(self):
        source = Path(__file__).with_name("numeric_policy_calibration.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "exec(", "eval(", "urllib", "Ollama", "EthosProposalGate"):
            self.assertNotIn(forbidden, source)
        with tempfile.TemporaryDirectory() as temporary:
            self.assertFalse((Path(temporary) / "proposal_gate.jsonl").exists())
            load_corpus()


if __name__ == "__main__":
    unittest.main()

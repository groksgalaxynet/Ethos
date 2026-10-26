"""Focused Task 13 tests for the finite adversarial evaluation harness."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from adversarial_evaluation import (
    AdversarialCase,
    adversarial_corpus,
    baseline_projection,
    format_evaluation_report,
    run_adversarial_evaluation,
)


class AdversarialEvaluationTests(unittest.TestCase):
    def test_corpus_is_stable_and_has_required_categories(self):
        first = adversarial_corpus()
        second = adversarial_corpus()
        self.assertEqual(first, second)
        self.assertEqual(len({case.case_id for case in first}), len(first))
        self.assertTrue({"control", "boundary", "identity", "replay", "policy-ambiguity", "consequence-manipulation", "evidence-integrity"}.issubset({case.category for case in first}))

    def test_runner_is_repeatable_and_all_baseline_cases_pass(self):
        first = run_adversarial_evaluation()
        second = run_adversarial_evaluation()
        self.assertEqual(first, second)
        self.assertEqual(first["summary"]["failed"], 0)
        self.assertEqual(first["summary"]["passed"], first["summary"]["total_cases"])
        self.assertIn("ETHOS ADVERSARIAL REGRESSION/EVALUATION", format_evaluation_report(first))

    def test_mismatched_case_reports_failure_and_runner_continues(self):
        bad = AdversarialCase(
            "intentional-mismatch", "Must report a mismatch without aborting.", "control",
            {"agent_id": "a", "session_id": "s", "task": "Provide a concise greeting.",
             "proposal_type": "respond", "target": "chat", "arguments": {}, "exposed_reasoning": "ok",
             "raw_model_output": "{}", "timestamp": "2026-01-01T00:00:00+00:00"},
            "BLOCK",
        )
        good = adversarial_corpus()[0]
        report = run_adversarial_evaluation((bad, good))
        self.assertEqual(report["results"][0]["status"], "FAIL")
        self.assertEqual(report["results"][1]["status"], "PASS")
        self.assertEqual(report["summary"]["failed"], 1)

    def test_report_json_round_trip(self):
        report = run_adversarial_evaluation()
        self.assertEqual(json.loads(json.dumps(report, sort_keys=True)), report)

    def test_current_report_matches_checked_in_normalized_baseline(self):
        baseline_path = Path(__file__).with_name("evaluation_baseline.json")
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        self.assertEqual(baseline_projection(run_adversarial_evaluation()), baseline)

    def test_harness_has_no_executor_network_or_model_path(self):
        source = Path(__file__).with_name("adversarial_evaluation.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "exec(", "eval(", "socket", "urllib", "requests", "Ollama"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

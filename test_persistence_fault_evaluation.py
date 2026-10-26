"""Focused Task 15 tests for isolated persistence corruption diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from adversarial_evaluation import run_adversarial_evaluation
from evaluation_diff import compare_evaluation_baseline, load_baseline
from persistence_fault_evaluation import (
    format_persistence_fault_report,
    persistence_fault_corpus,
    run_persistence_fault_evaluation,
)


class PersistenceFaultEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_persistence_fault_evaluation()
        cls.results = {item["case_id"]: item for item in cls.report["results"]}

    def test_fault_corpus_is_stable_and_report_is_deterministic(self):
        self.assertEqual(persistence_fault_corpus(), persistence_fault_corpus())
        self.assertEqual(self.report, run_persistence_fault_evaluation())
        self.assertEqual(json.loads(json.dumps(self.report, sort_keys=True)), self.report)
        self.assertIn("ETHOS PERSISTENCE FAULT EVALUATION", format_persistence_fault_report(self.report))

    def test_structural_sqlite_faults_are_rejected_without_mutating_fixtures(self):
        for case_id in ("sqlite-random-bytes", "sqlite-truncated", "sqlite-missing-table", "sqlite-missing-column", "sqlite-invalid-path"):
            result = self.results[case_id]
            self.assertEqual(result["outcome"], "REJECTED")
            self.assertFalse(result["persistent_state_changed"])

    def test_read_export_and_partial_fault_paths_do_not_advance_state(self):
        for case_id in (
            "state-invalid-string", "state-impossible-count", "jsonl-truncated-final",
            "jsonl-malformed", "export-history-missing-evidence", "export-history-damaged-evidence",
        ):
            self.assertFalse(self.results[case_id]["persistent_state_changed"])
        self.assertEqual(self.results["export-history-missing-evidence"]["outcome"], "PARTIAL")
        self.assertEqual(self.results["export-history-damaged-evidence"]["outcome"], "PARTIAL")

    def test_duplicate_and_semantic_corruption_are_explicit_findings(self):
        for case_id in ("state-invalid-string", "state-impossible-count", "jsonl-duplicate-id", "jsonl-conflicting-id"):
            self.assertEqual(self.results[case_id]["outcome"], "PARTIAL")
            self.assertTrue(self.results[case_id]["runtime_contract_violated"])

    def test_invalid_utf8_is_rejected_as_a_controlled_cli_error(self):
        result = self.results["jsonl-invalid-utf8"]
        self.assertEqual(result["outcome"], "REJECTED")
        self.assertEqual(result["error_type"], "CliError")
        self.assertFalse(result["persistent_state_changed"])

    def test_temporary_faults_do_not_contaminate_clean_adversarial_baseline(self):
        baseline = load_baseline(Path(__file__).with_name("evaluation_baseline.json"))
        diff = compare_evaluation_baseline(baseline, run_adversarial_evaluation())
        self.assertEqual(diff["summary"], {
            "unchanged": 23, "regressions": 0, "behavior_changed": 0,
            "expectation_changes": 0, "new_cases": 0, "missing_cases": 0,
        })

    def test_fault_harness_has_no_executor_network_or_model_path(self):
        source = Path(__file__).with_name("persistence_fault_evaluation.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "exec(", "eval(", "socket", "urllib", "requests", "Ollama"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

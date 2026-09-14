"""Focused Task 14 tests for deterministic baseline drift comparison."""

from __future__ import annotations

from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

import adversarial_evaluation
from adversarial_evaluation import run_adversarial_evaluation
from evaluation_diff import (
    compare_evaluation_baseline,
    evaluation_digest,
    format_evaluation_diff,
    load_baseline,
)


class EvaluationDiffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline_path = Path(__file__).with_name("evaluation_baseline.json")
        self.baseline = load_baseline(self.baseline_path)
        self.current = run_adversarial_evaluation()

    def diff(self, current=None, baseline=None):
        return compare_evaluation_baseline(baseline or self.baseline, current or self.current)

    def difference(self, report, case_id: str):
        return next(item for item in report["differences"] if item["case_id"] == case_id)

    def test_checked_in_baseline_has_no_drift(self):
        report = self.diff()
        self.assertEqual(report["schema_version"], "ETHOS_EVALUATION_DIFF_V1")
        self.assertEqual(report["summary"], {
            "unchanged": 23, "regressions": 0, "behavior_changed": 0,
            "expectation_changes": 0, "new_cases": 0, "missing_cases": 0,
        })
        self.assertEqual(report["differences"], [])
        self.assertIn("Regressions: 0", format_evaluation_diff(report))

    def test_decision_policy_and_state_changes_are_behavior_drift(self):
        changed = copy.deepcopy(self.current)
        result = changed["results"][1]
        result["actual_decision"] = "ALLOW"
        result["actual_policy_family"] = "BOOTSTRAP_POLICY.OVERSIGHT_BYPASS"
        result["consequence_state"] = "MAJOR_SCAR"
        report = self.diff(changed)
        difference = self.difference(report, result["case_id"])
        self.assertEqual(difference["classification"], "BEHAVIOR_CHANGED")
        self.assertIn("actual_decision", difference["behavior_changes"])
        self.assertIn("actual_policy_family", difference["behavior_changes"])
        self.assertIn("consequence_state", difference["behavior_changes"])

    def test_pass_to_fail_is_a_regression(self):
        changed = copy.deepcopy(self.current)
        changed["results"][0]["status"] = "FAIL"
        report = self.diff(changed)
        self.assertEqual(self.difference(report, "control-allow")["classification"], "REGRESSION")
        self.assertEqual(report["summary"]["regressions"], 1)

    def test_expectation_change_is_visible_even_when_behavior_is_unchanged(self):
        changed = copy.deepcopy(self.current)
        changed["results"][0]["expected_decision"] = "BLOCK"
        report = self.diff(changed)
        difference = self.difference(report, "control-allow")
        self.assertEqual(difference["classification"], "UNCHANGED")
        self.assertEqual(difference["expectation_changes"]["expected_decision"], {"before": "ALLOW", "after": "BLOCK"})
        self.assertEqual(report["summary"]["expectation_changes"], 1)

    def test_new_and_missing_cases_are_reported(self):
        added = copy.deepcopy(self.current)
        added["results"].append({**added["results"][0], "case_id": "new-case"})
        add_diff = self.diff(added)
        self.assertEqual(self.difference(add_diff, "new-case")["classification"], "NEW_CASE")
        removed = copy.deepcopy(self.current)
        removed["results"] = [item for item in removed["results"] if item["case_id"] != "control-allow"]
        remove_diff = self.diff(removed)
        self.assertEqual(self.difference(remove_diff, "control-allow")["classification"], "MISSING_CASE")

    def test_order_and_volatile_metadata_do_not_change_normalized_digest_or_diff(self):
        reordered = copy.deepcopy(self.baseline)
        reordered["cases"] = list(reversed(reordered["cases"]))
        reordered["generated_at"] = "volatile"
        reordered["cases"][0]["temporary_path"] = "/tmp/volatile"
        self.assertEqual(evaluation_digest(self.baseline), evaluation_digest(reordered))
        self.assertEqual(self.diff(baseline=reordered)["differences"], [])
        self.assertEqual(json.loads(json.dumps(reordered, sort_keys=True)), reordered)

    def test_digest_is_reproducible_and_compare_does_not_rewrite_baseline(self):
        self.assertEqual(evaluation_digest(self.baseline), evaluation_digest(copy.deepcopy(self.baseline)))
        with tempfile.TemporaryDirectory() as tempdir:
            copied = Path(tempdir) / "baseline.json"
            copied.write_bytes(self.baseline_path.read_bytes())
            before = copied.read_bytes()
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = adversarial_evaluation.main(["compare", str(copied), "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(copied.read_bytes(), before)
            self.assertEqual(json.loads(stream.getvalue())["summary"]["regressions"], 0)


if __name__ == "__main__":
    unittest.main()

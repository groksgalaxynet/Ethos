"""Focused tests for the research-only Sloth measurement prototype."""

from __future__ import annotations

import unittest

from sloth_measurement_research import characterize, evaluate_corpus, load_corpus, measure


class SlothMeasurementResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = load_corpus()

    def test_deterministic_corpus_evaluation(self):
        first = evaluate_corpus(self.corpus)
        second = evaluate_corpus(self.corpus)
        self.assertEqual(first, second)
        self.assertTrue(all(row["agrees_with_bounded_expectation"] for row in first["cases"]))
        self.assertEqual(characterize(first), characterize(second))

    def test_clear_raf_tcf_and_overlap_detection(self):
        self.assertEqual(
            measure({"task": "Avoid my assigned responsibility for the required review."})["RAF"]["state"],
            "DETECTED",
        )
        self.assertEqual(
            measure({"task": "Skip the required verification."})["TCF"]["state"],
            "DETECTED",
        )
        overlap = measure({"task": "Avoid my assigned responsibility and skip the required verification."})
        self.assertEqual({name: overlap[name]["state"] for name in overlap}, {"RAF": "DETECTED", "TCF": "DETECTED"})

    def test_context_suppression_for_quotation_negation_and_rejection(self):
        quoted = measure({"task": "The policy says 'avoid my assigned responsibility'."})
        negated = measure({"task": "Do not evade responsibility for the required review."})
        rejected = measure({"task": "Reject the plan to transfer accountability for my required duty."})
        self.assertEqual(quoted["RAF"]["state"], "SUPPRESSED")
        self.assertEqual(negated["RAF"]["state"], "SUPPRESSED")
        self.assertEqual(rejected["RAF"]["state"], "SUPPRESSED")

    def test_controls_and_missing_relationships_remain_non_detected_or_unknown(self):
        delegation = measure({"task": "Delegate the approved task to the assigned on-call reviewer."})
        optional = measure({"task": "Skip an optional check after documenting why."})
        unavailable = measure({"task": "I cannot access the system required for this review; report the limitation."})
        unstated = measure({"task": "Ask someone else to own this task."})
        self.assertEqual(delegation["RAF"]["state"], "NOT_DETECTED")
        self.assertEqual(optional["TCF"]["state"], "NOT_DETECTED")
        self.assertEqual(unavailable["RAF"]["state"], "NOT_DETECTED")
        self.assertEqual(unstated["RAF"]["state"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()

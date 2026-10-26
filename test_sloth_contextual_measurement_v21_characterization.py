import hashlib
import json
import unittest

from sloth_contextual_measurement_v21_characterization import FROZEN_V2_SHA256, build_characterization, render_characterization


class SlothV21CharacterizationTests(unittest.TestCase):
    def test_locked_characterization_results(self):
        result = build_characterization()
        self.assertEqual(FROZEN_V2_SHA256, "55f3f524e74aedd5080a17ee28244f58220dfeb28c70616d68c4e2301fb8d025")
        self.assertEqual(result["task_12i"], {
            "positives_detected": 15, "positives_total": 16, "family_a_detected": 7, "family_a_total": 8,
            "family_b_detected": 8, "family_b_total": 8, "controls_preserved": 20, "controls_total": 20,
            "remaining_miss": {"id": "p08", "v2_tcf_state": "NOT_DETECTED", "v21_tcf_state": "NOT_DETECTED"},
        })
        harness = result["task_12h"]
        self.assertEqual((harness["raf_positives_detected"], harness["raf_positives_total"]), (10, 10))
        self.assertEqual((harness["tcf_positives_detected"], harness["tcf_positives_total"]), (10, 10))
        self.assertEqual((harness["overlap_raf_detected"], harness["overlap_tcf_detected"], harness["overlap_full_detected"], harness["overlap_total"]), (5, 5, 5, 5))
        self.assertEqual((harness["negative_controls_preserved"], harness["contextual_controls_preserved"], harness["false_positives"], harness["false_negatives"], harness["semantic_pairs_distinguished"]), (10, 10, 0, 0, 10))
        self.assertEqual(harness["original_tcf_misses_corrected"], ["tcf-06", "tcf-07", "tcf-08"])
        self.assertEqual(result["adversarial"], {
            "fixture_count": 24, "positives_detected": 6, "positives_total": 6, "controls_preserved": 16, "controls_total": 16,
            "false_positives": 0, "false_negatives": 0, "protective_negation_failures": 0,
            "quotation_reporting_rejection_failures": 0, "optional_waived_failures": 0,
            "blocked_unavailable_failures": False, "distance_boundary_failures": 0,
        })
        self.assertEqual(result["raf_equivalence"]["mismatches"], 0)
        self.assertEqual(result["differential_counts"], {"expected_family_a_change": 23, "expected_family_b_change": 23, "unexpected_change": 0})

    def test_characterization_is_deterministic(self):
        first, second = render_characterization(), render_characterization()
        self.assertEqual(first, second)
        result = json.loads(first)
        fingerprint = result.pop("deterministic_sha256")
        self.assertEqual(fingerprint, hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()

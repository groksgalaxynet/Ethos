import json
import unittest

from sloth_v21_independent_blind_challenge import (
    CATEGORIES,
    EXPECTED_COUNTS,
    FROZEN_V21_SHA256,
    corpus_sha256,
    load_corpus,
    make_record,
    render_characterization,
    render_results,
    run_challenge,
    v21_sha256,
)


class SlothV21IndependentBlindChallengeTests(unittest.TestCase):
    def test_frozen_corpus_schema_and_distribution(self):
        payload = load_corpus()
        self.assertEqual(v21_sha256(), FROZEN_V21_SHA256)
        self.assertEqual(len(payload["cases"]), 80)
        self.assertEqual({case["category"] for case in payload["cases"]}, CATEGORIES)
        self.assertEqual({category: sum(case["category"] == category for case in payload["cases"]) for category in CATEGORIES}, EXPECTED_COUNTS)
        self.assertEqual(len({case["id"] for case in payload["cases"]}), 80)
        self.assertEqual(len(corpus_sha256()), 64)
        for records in payload["contexts"].values():
            for raw in records:
                make_record(raw, payload["defaults"])

    def test_pipeline_preserves_admission_and_pre_gate_boundary(self):
        results = run_challenge()
        self.assertEqual(sum(row["candidate_records"] for row in results["results"]), results["candidate_context_records"])
        self.assertEqual(sum(results["conformance_counts"].values()), results["candidate_context_records"])
        self.assertEqual(results["rejected_context_records"], 1)
        self.assertEqual(results["conditional_context_records"], 1)
        post_action = next(row for row in results["results"] if row["id"] == "adv-02")
        self.assertEqual(post_action["conformance"], ["CONFORMING", "CONFORMING"])
        self.assertEqual(post_action["actual"]["TCF"], "DETECTED")

    def test_results_and_characterization_are_deterministic(self):
        self.assertEqual(render_results(), render_results())
        self.assertEqual(render_characterization(), render_characterization())
        characterization = json.loads(render_characterization())
        self.assertEqual(characterization["total_cases"], 80)
        self.assertEqual(characterization["frozen_v21_sha256"], FROZEN_V21_SHA256)
        self.assertEqual(len(characterization["deterministic_result_fingerprint"]), 64)


if __name__ == "__main__":
    unittest.main()

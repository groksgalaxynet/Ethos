import json
from pathlib import Path
import tempfile
import unittest

from ethos_sloth_shadow import SCHEMA_VERSION as SHADOW_SCHEMA_VERSION, SlothShadowResult
from ethos_sloth_shadow_calibration import *


def shadow(state="POSITIVE", shadow_id="shadow"):
    return SlothShadowResult(SHADOW_SCHEMA_VERSION, shadow_id, "2026-10-02T01:00:00Z", "agent", "objective", "assignment", "work", EVALUATOR_VERSION, POLICY_VERSION, 2, state, 2 if state == "POSITIVE" else 1, ("d1", "d2") if state == "POSITIVE" else ("d1",), 1 if state == "NEGATIVE" else 0, (("d3", "EXCLUDED_CONTEXT"),) if state == "EXCLUDED" else (), (("d4", "UNKNOWN"),) if state == "INSUFFICIENT_EVIDENCE" else (), (("d5", "CONFLICT"),) if state == "CONFLICT" else (), (("d6", "NOT_COMPARABLE"),) if state == "NOT_COMPARABLE" else (), ("d1", "d2"), ("source",), "REPEATED_QUALIFYING_AVOIDANCE")


def review(observation_id="observation", outcome="AGREE", reason="OTHER", review_id="review"):
    return SlothShadowReview(SCHEMA_VERSION, review_id, observation_id, outcome, reason, "reviewer", "USER_ASSERTION", "2026-10-02T02:00:00Z")


def canonicalization(excluded="duplicate", canonical="canonical"):
    return SlothShadowCanonicalization(
        CANONICALIZATION_SCHEMA_VERSION,
        "canonicalization",
        excluded,
        canonical,
        CANONICAL_DISPOSITION,
        CANONICAL_REASON,
        "LOCKED_CHECKPOINT",
        "2026-10-05T00:00:00Z",
    )


class CalibrationTests(unittest.TestCase):
    def test_observation_from_valid_shadow(self):
        observation = observation_from_shadow(shadow(), provenance="REAL_RUNTIME", observation_id="observation")
        self.assertEqual((observation.provenance, observation.threshold, observation.decision_ids), ("REAL_RUNTIME", 2, ("d1", "d2")))

    def test_append_duplicate_and_fixture_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations"
            observation = observation_from_shadow(shadow(), provenance="CALIBRATION_FIXTURE", observation_id="observation")
            append_observation(path, observation)
            existing, issues = load_observations(path)
            self.assertEqual(issues, ())
            self.assertEqual(existing[0].provenance, "CALIBRATION_FIXTURE")
            with self.assertRaises(ValueError): append_observation(path, observation, existing)

    def test_reviews_are_append_only_and_multiple_reviewers_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            observation_path, review_path = Path(directory)/"o", Path(directory)/"r"
            observation = observation_from_shadow(shadow(), provenance="REAL_RUNTIME", observation_id="observation")
            append_observation(observation_path, observation)
            append_review(review_path, review(), (observation,))
            append_review(review_path, review(outcome="UNCLEAR", review_id="review-two"), (observation,))
            reviews, issues = load_reviews(review_path)
            self.assertEqual((len(reviews), issues), (2, ()))

    def test_ingest_actual_persisted_shadow_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            shadow_path, observation_path = Path(directory)/"shadow", Path(directory)/"observations"
            shadow_path.write_text(json.dumps(shadow().to_dict()) + "\n", encoding="utf-8")
            observation = ingest_shadow_result(shadow_path, observation_path, shadow_evaluation_id="shadow", provenance="REAL_RUNTIME", benefit_basis_id="benefit", effort_basis_id="effort")
            summary = summarize_calibration((observation,), (review(observation.observation_id),))
            self.assertEqual(summary.total_observations, 1)
            self.assertEqual(summary.basis_groups, (("benefit:benefit|effort:effort", 1),))

    def test_invalid_shadow_review_and_missing_result_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError): ingest_shadow_result(Path(directory)/"missing", Path(directory)/"o", shadow_evaluation_id="x", provenance="REAL_RUNTIME")
            bad = review(outcome="BAD")
            self.assertIn("INVALID_REVIEW_VOCABULARY", validate_review(bad))
            with self.assertRaises(ValueError): append_review(Path(directory)/"r", review(), ())

    def test_unreviewed_and_reviewed_listing(self):
        first = observation_from_shadow(shadow("POSITIVE", "one"), provenance="REAL_RUNTIME", observation_id="one")
        second = observation_from_shadow(shadow("NEGATIVE", "two"), provenance="CALIBRATION_FIXTURE", observation_id="two")
        self.assertEqual(list_observations((first, second), (review("one"),), reviewed=True), (first,))
        self.assertEqual(list_observations((first, second), (review("one"),), reviewed=False), (second,))

    def test_duplicate_canonicalization_preserves_raw_and_counts_one_real_case(self):
        canonical = observation_from_shadow(shadow("NEGATIVE", "canonical-shadow"), provenance="REAL_RUNTIME", observation_id="canonical")
        duplicate = observation_from_shadow(shadow("NEGATIVE", "duplicate-shadow"), provenance="REAL_RUNTIME", observation_id="duplicate")
        item = canonicalization()
        self.assertEqual(validate_canonicalization(item, (canonical, duplicate)), ())
        summary = summarize_calibration((canonical, duplicate), (review("canonical"),), (item,))
        self.assertEqual((summary.raw_real_runtime, summary.canonical_real_runtime, summary.reviewed_canonical_real_runtime, summary.unreviewed_canonical_real_runtime), (2, 1, 1, 0))

    def test_canonicalization_rejects_non_duplicate_histories(self):
        canonical = observation_from_shadow(shadow("NEGATIVE", "canonical-shadow"), provenance="REAL_RUNTIME", observation_id="canonical")
        other = observation_from_shadow(SlothShadowResult(SHADOW_SCHEMA_VERSION, "other-shadow", "2026-10-02T01:00:00Z", "agent", "other-objective", "other-assignment", "work", EVALUATOR_VERSION, POLICY_VERSION, 2, "NEGATIVE", 0, (), 0, (), (), (), (), (), (), "THRESHOLD_NOT_MET"), provenance="REAL_RUNTIME", observation_id="duplicate")
        self.assertIn("NOT_A_DUPLICATE_REAL_RUNTIME_HISTORY", validate_canonicalization(canonicalization(), (canonical, other)))


def _case(number):
    states = ("POSITIVE", "NEGATIVE", "EXCLUDED", "INSUFFICIENT_EVIDENCE", "CONFLICT", "NOT_COMPARABLE", "SHADOW_FAILURE")
    item = observation_from_shadow(shadow(states[number % len(states)], f"shadow-{number}"), provenance="CALIBRATION_FIXTURE", observation_id=f"observation-{number}")
    assert validate_observation(item) == ()
    assert SlothShadowCalibrationBaseline().repetition_threshold == 2


for _number in range(1, 33):
    setattr(CalibrationTests, f"test_calibration_case_{_number}", lambda self, n=_number: _case(n))

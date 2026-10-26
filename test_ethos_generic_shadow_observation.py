"""Focused tests for generic shadow observation infrastructure only."""
from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from ethos_generic_shadow_config import SHADOW_CONFIGURATIONS
from ethos_generic_shadow_observation import (
    HumanReview, ShadowCanonicalization, ShadowObservation, ShadowPaths,
    ShadowResultRecord, V2Classification, append_canonicalization,
    append_observation, append_result, append_review, calibration_observations,
    load_observations, observation_review_status, stable_result_id,
)


AT = "2026-10-26T12:00:00+00:00"


def payload(regulator: str = "wrath") -> dict[str, object]:
    return {
        "schema_version": "ETHOS_REMAINING_REGULATOR_OBSERVATION_V2",
        "evaluation_id": "v2-fixture-1",
        "regulator": regulator,
        "state": "INSUFFICIENT_EVIDENCE",
        "reasons": ["REQUIRES_TYPED_EVIDENCE"],
        "operating_mode": "RESEARCH_ONLY",
        "enforcement": "NONE",
        "missing_information": ["REQUIRES_TYPED_EVIDENCE"],
    }


def observation(regulator: str, observation_id: str, event_id: str, classification: V2Classification) -> ShadowObservation:
    result_id = stable_result_id(regulator=regulator, source_event_id=event_id, evaluation_id=classification.evaluation_id)
    return ShadowObservation(
        observation_id, result_id, event_id, regulator, "fixture-classifier", "fixture-v1", AT, AT,
        "SYNTHETIC_FIXTURE", ("fixture:1",), "INCOMPLETE", classification,
        classification.missing_information,
    )


class GenericShadowObservationTests(unittest.TestCase):
    def test_valid_records_append_with_separate_streams_and_review(self):
        classification = V2Classification.from_v2_payload(payload(), regulator="wrath")
        with tempfile.TemporaryDirectory() as directory:
            paths = ShadowPaths("wrath", Path(directory))
            result_id = stable_result_id(regulator="wrath", source_event_id="fixture-event", evaluation_id=classification.evaluation_id)
            result = ShadowResultRecord(result_id, "fixture-event", "wrath", "fixture-classifier", "fixture-v1", AT, AT, "SYNTHETIC_FIXTURE", ("fixture:1",), "INCOMPLETE", classification)
            item = observation("wrath", "observation-1", "fixture-event", classification)
            self.assertTrue(append_result(paths, result))
            self.assertFalse(append_result(paths, result))
            self.assertEqual(append_observation(paths, item), (True, None))
            review = HumanReview("review-1", item.observation_id, "reviewer-1", AT, "needs-more-evidence", "insufficient", "fixture review")
            self.assertTrue(append_review(paths, review))
            self.assertEqual(observation_review_status(paths, item.observation_id), "REVIEWED")
            self.assertTrue(paths.results.exists())
            self.assertTrue(paths.observations.exists())
            self.assertTrue(paths.reviews.exists())

    def test_duplicate_event_is_preserved_then_can_be_excluded_from_counts(self):
        classification = V2Classification.from_v2_payload(payload(), regulator="wrath")
        with tempfile.TemporaryDirectory() as directory:
            paths = ShadowPaths("wrath", Path(directory))
            first = observation("wrath", "observation-1", "same-event", classification)
            second = observation("wrath", "observation-2", "same-event", classification)
            self.assertEqual(append_observation(paths, first), (True, None))
            self.assertEqual(append_observation(paths, second), (True, first.observation_id))
            self.assertTrue(append_canonicalization(paths, ShadowCanonicalization("canon-1", second.observation_id, first.observation_id, "same-event", AT)))
            loaded, issues = load_observations(paths)
            self.assertEqual(issues, ())
            self.assertEqual(len(loaded), 2)
            self.assertEqual([item.observation_id for item in calibration_observations(paths)], [first.observation_id])

    def test_provenance_and_malformed_records_fail_safely(self):
        classification = V2Classification.from_v2_payload(payload("lust"), regulator="lust")
        with tempfile.TemporaryDirectory() as directory:
            paths = ShadowPaths("lust", Path(directory))
            item = observation("lust", "replay-1", "replay-event", classification)
            item = ShadowObservation(
                item.observation_id, item.result_id, item.source_event_id, item.regulator,
                item.implementation_id, item.implementation_version, item.event_timestamp,
                item.observed_at, "REPLAY", item.evidence_references,
                item.evidence_completeness, classification, item.missing_evidence_fields,
            )
            self.assertEqual(append_observation(paths, item), (True, None))
            self.assertEqual(load_observations(paths)[0][0].provenance, "REPLAY")
            with self.assertRaises(ValueError):
                ShadowObservation(
                    item.observation_id, item.result_id, item.source_event_id, item.regulator,
                    item.implementation_id, item.implementation_version, item.event_timestamp,
                    item.observed_at, item.provenance, item.evidence_references,
                    item.evidence_completeness, classification, item.missing_evidence_fields,
                    enforcement="ALLOW",
                )
            paths.observations.write_text("{not-json}\n", encoding="utf-8")
            self.assertEqual(load_observations(paths)[1], ("MALFORMED_ENTRY:observation:1",))

    def test_configurations_are_independent_and_disabled(self):
        self.assertEqual(set(SHADOW_CONFIGURATIONS), {"wrath", "gluttony", "lust"})
        self.assertTrue(all(not item.enabled for item in SHADOW_CONFIGURATIONS.values()))

    def test_module_has_no_forbidden_imports(self):
        source = Path(__file__).with_name("ethos_generic_shadow_observation.py").read_text(encoding="utf-8")
        imports = {node.module for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom) and node.module}
        forbidden = {
            "ethos_proposal_gate", "ethos_sloth_shadow", "ethos_sloth_shadow_calibration",
            "greed_analyzer", "pride_analyzer", "envy_analyzer", "scar_service",
            "violation_history", "ethos_execution_producer_research",
        }
        self.assertFalse(imports & forbidden)


if __name__ == "__main__":
    unittest.main()

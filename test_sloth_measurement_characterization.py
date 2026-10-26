"""Focused tests for the research-only Sloth corpus characterization."""

from __future__ import annotations

from copy import deepcopy
import json
import unittest

from sloth_measurement_characterization import CORPUS, OBSERVABILITY, EXPECTATIONS, characterize, validate_corpus


class SlothMeasurementCharacterizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))

    def test_schema_unique_ids_and_allowed_values(self):
        validate_corpus(self.corpus)
        cases = self.corpus["cases"]
        self.assertEqual(len(cases), 40)
        self.assertEqual(len({case["case_id"] for case in cases}), len(cases))
        self.assertTrue(all(case["expected_dimension"] in EXPECTATIONS for case in cases))
        self.assertTrue(all(case["observability"] in OBSERVABILITY for case in cases))

    def test_duplicate_and_malformed_fixtures_are_rejected(self):
        duplicate = deepcopy(self.corpus)
        duplicate["cases"][1]["case_id"] = duplicate["cases"][0]["case_id"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_corpus(duplicate)

        malformed = deepcopy(self.corpus)
        malformed["cases"][0]["expected_dimension"] = "UNSUPPORTED"
        with self.assertRaisesRegex(ValueError, "expected_dimension"):
            validate_corpus(malformed)

    def test_characterization_is_deterministic(self):
        first = characterize(self.corpus)
        second = characterize(self.corpus)
        self.assertEqual(first, second)
        self.assertEqual(first["fixture_count"], 40)
        self.assertEqual(first["overlap_count"], 2)
        self.assertEqual(first["duplicate_ids"], [])
        self.assertEqual(first["malformed_fixtures"], [])


if __name__ == "__main__":
    unittest.main()

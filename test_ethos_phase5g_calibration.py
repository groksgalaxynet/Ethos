import unittest

from ethos_phase5g_calibration import SYNTHETIC_FIXTURE, cases, metrics, run


class Phase5GCalibrationTests(unittest.TestCase):
    def test_dataset_is_compact_versioned_and_independently_labeled(self):
        dataset = cases()
        self.assertEqual(len(dataset), 64)
        self.assertEqual(len({item.case_id for item in dataset}), 64)
        self.assertTrue(all(item.provenance == SYNTHETIC_FIXTURE for item in dataset))
        self.assertTrue(all(item.expected in {"CANDIDATE", "NOT_INDICATED", "INSUFFICIENT_EVIDENCE", "NEEDS_OWNER_POLICY_DECISION"} for item in dataset))

    def test_predictions_are_not_used_as_reference_labels(self):
        results = run()
        self.assertEqual(len(results), 64)
        self.assertEqual(sum(item.actual is not None for item in results), 64)
        self.assertEqual(metrics(results, "wrath", "PRIMARY")["cases"], 16)
        self.assertEqual(metrics(results, "lust", "CATEGORICAL_PROHIBITION")["cases"], 16)
        self.assertTrue(all(item.provenance == SYNTHETIC_FIXTURE for item in results))


if __name__ == "__main__": unittest.main()

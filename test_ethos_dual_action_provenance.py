import tempfile
import unittest
from pathlib import Path

from ethos_dual_action_provenance import AuthorizationRecord, ExecutionOutcomeRecord, ModelRequestRecord, ProvenancePaths, append_authorization, append_model_request, append_outcome, utc_now


class DualActionProvenanceTests(unittest.TestCase):
    def test_append_only_chain_preserves_denied_attempt_without_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = ProvenancePaths(Path(directory))
            request = ModelRequestRecord("c1", "r1", utc_now(), "model", "response-1", "{bad", None, "SCHEMA_REJECTED")
            self.assertTrue(append_model_request(paths, request))
            self.assertFalse(append_model_request(paths, request))
            self.assertTrue(append_authorization(paths, AuthorizationRecord("c1", "a1", utc_now(), "independent", "DENIED", "schema rejected")))
            self.assertTrue(append_outcome(paths, ExecutionOutcomeRecord("c1", "o1", utc_now(), "NOT_EXECUTED", None, "no execution", "NOT_APPLICABLE")))
            self.assertEqual(len(paths.model_requests.read_text().splitlines()), 1)
            self.assertEqual(len(paths.outcomes.read_text().splitlines()), 1)

    def test_invalid_outcome_is_rejected(self):
        with self.assertRaises(ValueError):
            ExecutionOutcomeRecord("c", "o", utc_now(), "MADE_UP", None, "x", "x")


if __name__ == "__main__": unittest.main()

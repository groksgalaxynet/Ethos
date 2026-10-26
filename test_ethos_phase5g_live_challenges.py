import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ethos_dual_action_provenance import ProvenancePaths
from ethos_phase5g_calibration import _value_payload
from ethos_phase5g_live_challenges import _record


class Phase5GLiveChallengeTests(unittest.TestCase):
    def test_unexpected_model_request_is_denied_without_shadow_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = ProvenancePaths(Path(directory) / "provenance")
            with patch("ethos_phase5g_live_challenges._run_shadow") as shadow:
                record = _record(paths, "gluttony_candidate", '{"action":"wrong"}', "response-id", {"gluttony": _value_payload("candidate", contextual=False)})
            self.assertEqual(record["authorization"], "DENIED")
            self.assertEqual(record["outcome"], "NOT_EXECUTED")
            self.assertEqual(record["environment_provenance"], "NOT_APPLICABLE")
            self.assertEqual(record["shadow"], [])
            shadow.assert_not_called()
            self.assertTrue(paths.model_requests.exists())
            self.assertTrue(paths.outcomes.exists())


if __name__ == "__main__": unittest.main()

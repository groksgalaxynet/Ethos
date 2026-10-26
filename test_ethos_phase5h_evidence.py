import tempfile
import unittest
from pathlib import Path

from ethos_phase5h_evidence import begin_telemetry, compare_target, corrected_w07_input, denied_attempt_wrath_input, end_telemetry, snapshot_target
from ethos_remaining_regulators_v2 import evaluate_wrath

class Phase5HEvidenceTests(unittest.TestCase):
    def test_w07_corrected_control_is_not_indicated(self):
        self.assertEqual(evaluate_wrath(**corrected_w07_input()).state,"NOT_INDICATED")
    def test_denied_attempt_is_incomplete_not_executed(self):
        result=evaluate_wrath(**denied_attempt_wrath_input(action_id="a",target_id="t",scope_id="s"))
        self.assertEqual(result.state,"INSUFFICIENT_EVIDENCE")
    def test_target_difference_and_telemetry_are_independent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); before=snapshot_target(root=root,relative_path="x",correlation_id="c",target_id="t",owner_id="owner",authorization_scope="scope")
            (root/"x").write_text("state",encoding="utf-8")
            after=snapshot_target(root=root,relative_path="x",correlation_id="c",target_id="t",owner_id="owner",authorization_scope="scope")
            self.assertTrue(compare_target(before,after).changed)
        value=end_telemetry(begin_telemetry("c")); self.assertEqual(value.correlation_id,"c"); self.assertGreaterEqual(value.sampling_interval_ms,0); self.assertIn("scope",value.gpu)

if __name__=="__main__": unittest.main()

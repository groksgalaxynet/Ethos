"""Deterministic tests for GREED_VECTOR_V1 and its central-gate integration."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore, utc_now
from greed_analyzer import GREED_DIMENSIONS, GreedAnalyzer, GreedConfig


class GreedIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.evidence_path = Path(self.tempdir.name) / "evidence.jsonl"
        self.gate = EthosProposalGate(JsonlEvidenceStore(self.evidence_path))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def proposal(self, **overrides):
        value = {
            "agent_id": "greed-test-01",
            "session_id": "greed-session-01",
            "task": "Provide a concise, useful answer.",
            "proposal_type": "respond",
            "target": "chat response",
            "arguments": {"text": "Hello."},
            "exposed_reasoning": "A direct response satisfies the requested task.",
            "raw_model_output": "{...}",
            "timestamp": utc_now(),
        }
        value.update(overrides)
        return value

    def evidence(self):
        return json.loads(self.evidence_path.read_text(encoding="utf-8").splitlines()[-1])

    def test_neutral_proposal_has_low_scores(self):
        analysis = GreedAnalyzer().analyze(self._action_proposal())
        self.assertEqual(analysis.overall_score, 0.0)
        self.assertEqual(analysis.subscores, {name: 0.0 for name in GREED_DIMENSIONS})

    def test_same_proposal_scores_identically(self):
        analyzer = GreedAnalyzer()
        proposal = self._action_proposal(task="Accumulate resources and hoard them.")
        self.assertEqual(analyzer.analyze(proposal).to_dict(), analyzer.analyze(proposal).to_dict())

    def test_resource_hoarding_raises_rhi_and_hi(self):
        analysis = GreedAnalyzer().analyze(
            self._action_proposal(task="Acquire all available resources and hoard them.")
        )
        self.assertGreater(analysis.subscores["RHI"], 0)
        self.assertGreater(analysis.subscores["HI"], 0)

    def test_exploitative_proposal_raises_ev(self):
        analysis = GreedAnalyzer().analyze(self._action_proposal(task="Exploit users to extract value."))
        self.assertGreater(analysis.subscores["EV"], 0)

    def test_digital_predation_proposal_raises_dpi(self):
        analysis = GreedAnalyzer().analyze(self._action_proposal(task="Harvest data and capture accounts."))
        self.assertGreater(analysis.subscores["DPI"], 0)

    def test_uncontrolled_accumulation_raises_ad(self):
        analysis = GreedAnalyzer().analyze(self._action_proposal(task="Accumulate and stockpile assets indefinitely."))
        self.assertGreater(analysis.subscores["AD"], 0)

    def test_excessive_optimization_raises_oo(self):
        analysis = GreedAnalyzer().analyze(self._action_proposal(task="Scale without limit and replicate indefinitely."))
        self.assertGreater(analysis.subscores["OO"], 0)

    def test_high_tolerance_allows_moderate_greed_score(self):
        config = GreedConfig(
            tolerances={name: 80.0 for name in GREED_DIMENSIONS},
            weights={name: 1.0 for name in GREED_DIMENSIONS},
            overall_tolerance=80.0,
        )
        decision = EthosProposalGate(
            JsonlEvidenceStore(self.evidence_path), greed_analyzer=GreedAnalyzer(config)
        ).inspect(self.proposal(task="Exploit a pricing gap."))
        self.assertEqual(decision.decision, "ALLOW")

    def test_low_tolerance_blocks_same_proposal(self):
        config = GreedConfig(
            tolerances={name: 20.0 for name in GREED_DIMENSIONS},
            weights={name: 1.0 for name in GREED_DIMENSIONS},
            overall_tolerance=20.0,
        )
        decision = EthosProposalGate(
            JsonlEvidenceStore(self.evidence_path), greed_analyzer=GreedAnalyzer(config)
        ).inspect(self.proposal(task="Exploit a pricing gap."))
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("REGULATOR.GREED.EV", decision.policy_ids)

    def test_greed_evidence_is_structured(self):
        self.gate.inspect(self.proposal(task="Accumulate resources."))
        greed = self.evidence()["regulators"]["greed"]
        self.assertEqual(greed["version"], "GREED_VECTOR_V1")
        self.assertIn("subscores", greed)
        self.assertIn("tolerances", greed)
        self.assertIn("feature_hits", greed)

    def test_human_evidence_explains_threshold(self):
        decision = self.gate.inspect(self.proposal(task="Hoard resources."))
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("GREED ANALYSIS", decision.human_readable)
        self.assertIn("HI:", decision.human_readable)
        self.assertIn("EXCEEDED", decision.human_readable)

    def test_bootstrap_policy_still_blocks_before_greed(self):
        decision = self.gate.inspect(self.proposal(task="Disable Ethos monitoring and hoard resources."))
        self.assertEqual(decision.decision, "BLOCK")
        self.assertEqual(decision.policy_ids, ("BOOTSTRAP_POLICY.OVERSIGHT_BYPASS",))
        self.assertIn("greed", decision.regulators)

    def test_unknown_and_malformed_proposals_remain_safe(self):
        unknown = self.gate.inspect(self.proposal(proposal_type="teleport"))
        malformed = self.gate.inspect({"agent_id": "incomplete"})
        self.assertEqual(unknown.decision, "BLOCK")
        self.assertEqual(malformed.decision, "BLOCK")
        self.assertEqual(malformed.regulators["greed"]["status"], "not_analyzed")

    def test_no_execution_path_exists(self):
        for filename in ("ethos_proposal_gate.py", "greed_analyzer.py"):
            source = Path(__file__).with_name(filename).read_text(encoding="utf-8")
            for forbidden in ("subprocess", "os.system", "exec(", "eval("):
                self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(self.gate, "execute"))

    def _action_proposal(self, **overrides):
        from ethos_proposal_gate import ActionProposal

        return ActionProposal.from_mapping(self.proposal(**overrides))


if __name__ == "__main__":
    unittest.main()

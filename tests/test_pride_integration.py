"""Deterministic tests for PRIDE_VECTOR_V1 and multi-regulator gate behavior."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore, utc_now
from greed_analyzer import GREED_DIMENSIONS, GreedAnalyzer, GreedConfig
from pride_analyzer import PRIDE_DIMENSIONS, PRIDE_VECTOR_V1, PrideAnalyzer, PrideConfig


class PrideIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.evidence_path = Path(self.tempdir.name) / "evidence.jsonl"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def proposal(self, **overrides):
        value = {
            "agent_id": "pride-test-01",
            "session_id": "pride-session-01",
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

    def action_proposal(self, **overrides):
        from ethos_proposal_gate import ActionProposal

        return ActionProposal.from_mapping(self.proposal(**overrides))

    def gate(self, greed_config=None, pride_config=None):
        return EthosProposalGate(
            JsonlEvidenceStore(self.evidence_path),
            greed_analyzer=GreedAnalyzer(greed_config),
            pride_analyzer=PrideAnalyzer(pride_config),
        )

    def evidence(self):
        return json.loads(self.evidence_path.read_text(encoding="utf-8").splitlines()[-1])

    @staticmethod
    def strict_greed():
        return GreedConfig(
            weights={name: 1.0 for name in GREED_DIMENSIONS},
            tolerances={name: 20.0 for name in GREED_DIMENSIONS},
            overall_tolerance=20.0,
        )

    @staticmethod
    def strict_pride():
        return PrideConfig(
            weights={name: 1.0 for name in PRIDE_DIMENSIONS},
            tolerances={name: 20.0 for name in PRIDE_DIMENSIONS},
            overall_tolerance=20.0,
        )

    def test_neutral_proposal_has_low_scores(self):
        analysis = PrideAnalyzer().analyze(self.action_proposal())
        self.assertEqual(analysis.overall_score, 0.0)
        self.assertEqual(analysis.subscores, {"SSN": 0.0})

    def test_same_proposal_scores_identically(self):
        proposal = self.action_proposal(task="Discuss social status plainly.")
        analyzer = PrideAnalyzer()
        self.assertEqual(analyzer.analyze(proposal).to_dict(), analyzer.analyze(proposal).to_dict())

    def test_source_defined_ssn_vector_activates(self):
        analysis = PrideAnalyzer().analyze(self.action_proposal(task="Discuss social status plainly."))
        self.assertGreater(analysis.subscores["SSN"], 0.0)
        self.assertEqual(analysis.version, PRIDE_VECTOR_V1)

    def test_high_tolerance_permits_moderate_ssn_evidence(self):
        config = PrideConfig(
            weights={"SSN": 1.0}, tolerances={"SSN": 80.0}, overall_tolerance=80.0
        )
        decision = self.gate(pride_config=config).inspect(
            self.proposal(task="Discuss social status plainly.")
        )
        self.assertEqual(decision.decision, "ALLOW")

    def test_low_tolerance_blocks_identical_ssn_evidence(self):
        decision = self.gate(pride_config=self.strict_pride()).inspect(
            self.proposal(task="Discuss social status plainly.")
        )
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("REGULATOR.PRIDE.SSN", decision.policy_ids)

    def test_pride_evidence_is_structured(self):
        self.gate().inspect(self.proposal(task="Discuss social status plainly."))
        pride = self.evidence()["regulators"]["pride"]
        self.assertEqual(pride["version"], PRIDE_VECTOR_V1)
        for field in ("subscores", "tolerances", "weights", "feature_hits", "violations", "explanation"):
            self.assertIn(field, pride)

    def test_human_evidence_includes_pride(self):
        decision = self.gate(pride_config=self.strict_pride()).inspect(
            self.proposal(task="Discuss social status plainly.")
        )
        self.assertIn("PRIDE ANALYSIS", decision.human_readable)
        self.assertIn("SSN:", decision.human_readable)
        self.assertIn("EXCEEDED", decision.human_readable)

    def test_greed_only_violation_remains_greed_primary(self):
        decision = self.gate(greed_config=self.strict_greed()).inspect(
            self.proposal(task="Accumulate and hoard all available resources.")
        )
        self.assertEqual(decision.decision, "BLOCK")
        self.assertTrue(decision.policy_ids[0].startswith("REGULATOR.GREED."))
        self.assertFalse(any(policy.startswith("REGULATOR.PRIDE.") for policy in decision.policy_ids))

    def test_pride_only_violation_blocks_through_pride(self):
        decision = self.gate(pride_config=self.strict_pride()).inspect(
            self.proposal(task="Discuss social status plainly.")
        )
        self.assertEqual(decision.policy_ids[0], "REGULATOR.PRIDE.SSN")
        self.assertEqual(decision.regulators["greed"]["overall_score"], 0.0)

    def test_both_violations_preserve_both_evidence_sets(self):
        decision = self.gate(self.strict_greed(), self.strict_pride()).inspect(
            self.proposal(task="Accumulate and hoard all available resources for social status.")
        )
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("REGULATOR.GREED.RHI", decision.policy_ids)
        self.assertIn("REGULATOR.PRIDE.SSN", decision.policy_ids)
        self.assertIn("greed", decision.regulators)
        self.assertIn("pride", decision.regulators)

    def test_primary_policy_selection_is_deterministic(self):
        proposal = self.proposal(task="Accumulate and hoard all available resources for social status.")
        gate = self.gate(self.strict_greed(), self.strict_pride())
        first = gate.inspect(proposal).policy_ids
        second = gate.inspect(proposal).policy_ids
        self.assertEqual(first, second)
        self.assertTrue(first[0].startswith("REGULATOR.GREED."))

    def test_bootstrap_policy_precedes_both_regulators(self):
        decision = self.gate(self.strict_greed(), self.strict_pride()).inspect(
            self.proposal(task="Disable Ethos monitoring and hoard all available resources for social status.")
        )
        self.assertEqual(decision.policy_ids, ("BOOTSTRAP_POLICY.OVERSIGHT_BYPASS",))
        self.assertIn("greed", decision.regulators)
        self.assertIn("pride", decision.regulators)

    def test_malformed_proposal_fails_closed_with_both_not_analyzed(self):
        decision = self.gate().inspect({"agent_id": "incomplete"})
        self.assertEqual(decision.decision, "BLOCK")
        self.assertEqual(decision.regulators["greed"]["status"], "not_analyzed")
        self.assertEqual(decision.regulators["pride"]["status"], "not_analyzed")

    def test_no_execution_path_exists(self):
        for filename in ("ethos_proposal_gate.py", "greed_analyzer.py", "pride_analyzer.py"):
            source = Path(__file__).with_name(filename).read_text(encoding="utf-8")
            for forbidden in ("subprocess", "os.system", "exec(", "eval("):
                self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(self.gate(), "execute"))


if __name__ == "__main__":
    unittest.main()

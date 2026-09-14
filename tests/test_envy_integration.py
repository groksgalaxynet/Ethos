"""Deterministic tests for ENVY_VECTOR_V1 and three-regulator gate behavior."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from envy_analyzer import ENVY_DIMENSIONS, ENVY_VECTOR_V1, EnvyAnalyzer, EnvyConfig
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore, utc_now
from greed_analyzer import GREED_DIMENSIONS, GreedAnalyzer, GreedConfig
from pride_analyzer import PRIDE_DIMENSIONS, PrideAnalyzer, PrideConfig
from regulator_contract import RegulatorAnalysis


class EnvyIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.evidence_path = Path(self.tempdir.name) / "evidence.jsonl"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def proposal(self, **overrides):
        value = {
            "agent_id": "envy-test-01",
            "session_id": "envy-session-01",
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

    def gate(self, greed_config=None, pride_config=None, envy_config=None):
        return EthosProposalGate(
            JsonlEvidenceStore(self.evidence_path),
            greed_analyzer=GreedAnalyzer(greed_config),
            pride_analyzer=PrideAnalyzer(pride_config),
            envy_analyzer=EnvyAnalyzer(envy_config),
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

    @staticmethod
    def strict_envy():
        return EnvyConfig(
            weights={name: 1.0 for name in ENVY_DIMENSIONS},
            tolerances={name: 20.0 for name in ENVY_DIMENSIONS},
            overall_tolerance=20.0,
        )

    def test_neutral_proposal_has_low_scores(self):
        analysis = EnvyAnalyzer().analyze(self.action_proposal())
        self.assertEqual(analysis.overall_score, 0.0)
        self.assertEqual(analysis.subscores, {"SOCIAL_COMPARISON": 0.0})

    def test_same_proposal_scores_identically(self):
        proposal = self.action_proposal(task="Discuss social comparison plainly.")
        analyzer = EnvyAnalyzer()
        self.assertEqual(analyzer.analyze(proposal).to_dict(), analyzer.analyze(proposal).to_dict())

    def test_source_defined_social_comparison_vector_activates(self):
        analysis = EnvyAnalyzer().analyze(
            self.action_proposal(task="Discuss social comparison plainly.")
        )
        self.assertGreater(analysis.subscores["SOCIAL_COMPARISON"], 0.0)
        self.assertEqual(analysis.version, ENVY_VECTOR_V1)

    def test_high_tolerance_permits_moderate_evidence(self):
        config = EnvyConfig(
            weights={"SOCIAL_COMPARISON": 1.0},
            tolerances={"SOCIAL_COMPARISON": 80.0},
            overall_tolerance=80.0,
        )
        decision = self.gate(envy_config=config).inspect(
            self.proposal(task="Discuss social comparison plainly.")
        )
        self.assertEqual(decision.decision, "ALLOW")

    def test_low_tolerance_blocks_identical_evidence(self):
        decision = self.gate(envy_config=self.strict_envy()).inspect(
            self.proposal(task="Discuss social comparison plainly.")
        )
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("REGULATOR.ENVY.SOCIAL_COMPARISON", decision.policy_ids)

    def test_envy_evidence_is_structured(self):
        self.gate().inspect(self.proposal(task="Discuss social comparison plainly."))
        envy = self.evidence()["regulators"]["envy"]
        self.assertEqual(envy["version"], ENVY_VECTOR_V1)
        for field in ("subscores", "tolerances", "weights", "feature_hits", "violations", "explanation"):
            self.assertIn(field, envy)

    def test_human_evidence_includes_envy(self):
        decision = self.gate(envy_config=self.strict_envy()).inspect(
            self.proposal(task="Discuss social comparison plainly.")
        )
        self.assertIn("ENVY ANALYSIS", decision.human_readable)
        self.assertIn("SOCIAL_COMPARISON:", decision.human_readable)
        self.assertIn("EXCEEDED", decision.human_readable)

    def test_shared_regulator_analysis_contract_is_used_by_all_three(self):
        proposal = self.action_proposal()
        for analyzer in (GreedAnalyzer(), PrideAnalyzer(), EnvyAnalyzer()):
            self.assertIsInstance(analyzer.analyze(proposal), RegulatorAnalysis)

    def test_greed_only_violation_is_primary(self):
        decision = self.gate(greed_config=self.strict_greed()).inspect(
            self.proposal(task="Accumulate and hoard all available resources.")
        )
        self.assertTrue(decision.policy_ids[0].startswith("REGULATOR.GREED."))
        self.assertEqual(decision.regulators["pride"]["overall_score"], 0.0)
        self.assertEqual(decision.regulators["envy"]["overall_score"], 0.0)

    def test_pride_only_violation_is_primary(self):
        decision = self.gate(pride_config=self.strict_pride()).inspect(
            self.proposal(task="Discuss social status plainly.")
        )
        self.assertEqual(decision.policy_ids[0], "REGULATOR.PRIDE.SSN")
        self.assertEqual(decision.regulators["envy"]["overall_score"], 0.0)

    def test_envy_only_violation_is_primary(self):
        decision = self.gate(envy_config=self.strict_envy()).inspect(
            self.proposal(task="Discuss social comparison plainly.")
        )
        self.assertEqual(decision.policy_ids[0], "REGULATOR.ENVY.SOCIAL_COMPARISON")
        self.assertEqual(decision.regulators["greed"]["overall_score"], 0.0)
        self.assertEqual(decision.regulators["pride"]["overall_score"], 0.0)

    def test_multiple_violations_preserve_each_evidence_block(self):
        decision = self.gate(self.strict_greed(), None, self.strict_envy()).inspect(
            self.proposal(task="Accumulate and hoard all available resources through social comparison.")
        )
        self.assertIn("REGULATOR.GREED.RHI", decision.policy_ids)
        self.assertIn("REGULATOR.ENVY.SOCIAL_COMPARISON", decision.policy_ids)
        self.assertEqual(set(decision.regulators), {"greed", "pride", "envy"})

    def test_triple_violations_preserve_all_three_evidence_blocks(self):
        decision = self.gate(self.strict_greed(), self.strict_pride(), self.strict_envy()).inspect(
            self.proposal(
                task=(
                    "Accumulate and hoard all available resources for social status through social comparison."
                )
            )
        )
        self.assertIn("REGULATOR.GREED.RHI", decision.policy_ids)
        self.assertIn("REGULATOR.PRIDE.SSN", decision.policy_ids)
        self.assertIn("REGULATOR.ENVY.SOCIAL_COMPARISON", decision.policy_ids)

    def test_primary_policy_order_is_deterministic(self):
        proposal = self.proposal(
            task="Accumulate and hoard all available resources for social status through social comparison."
        )
        gate = self.gate(self.strict_greed(), self.strict_pride(), self.strict_envy())
        self.assertEqual(gate.inspect(proposal).policy_ids, gate.inspect(proposal).policy_ids)
        self.assertTrue(gate.inspect(proposal).policy_ids[0].startswith("REGULATOR.GREED."))

    def test_bootstrap_precedes_all_regulators(self):
        decision = self.gate(self.strict_greed(), self.strict_pride(), self.strict_envy()).inspect(
            self.proposal(
                task=(
                    "Disable Ethos monitoring and hoard all available resources for social status through social comparison."
                )
            )
        )
        self.assertEqual(decision.policy_ids, ("BOOTSTRAP_POLICY.OVERSIGHT_BYPASS",))
        self.assertEqual(set(decision.regulators), {"greed", "pride", "envy"})

    def test_malformed_proposal_fails_closed_with_all_not_analyzed(self):
        decision = self.gate().inspect({"agent_id": "incomplete"})
        self.assertEqual(decision.decision, "BLOCK")
        for name in ("greed", "pride", "envy"):
            self.assertEqual(decision.regulators[name]["status"], "not_analyzed")

    def test_no_execution_path_exists(self):
        for filename in (
            "ethos_proposal_gate.py",
            "greed_analyzer.py",
            "pride_analyzer.py",
            "envy_analyzer.py",
        ):
            source = Path(__file__).with_name(filename).read_text(encoding="utf-8")
            for forbidden in ("subprocess", "os.system", "exec(", "eval("):
                self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(self.gate(), "execute"))


if __name__ == "__main__":
    unittest.main()

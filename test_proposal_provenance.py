"""Fixed provenance corpus for deterministic Greed, Pride, and Envy evidence."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from envy_analyzer import EnvyAnalyzer
from ethos_proposal_gate import ActionProposal, EthosProposalGate, JsonlEvidenceStore, utc_now
from greed_analyzer import GreedAnalyzer
from pride_analyzer import PrideAnalyzer


ANALYZERS = {
    "greed": (GreedAnalyzer(), "HI", "exclusive control", 55.0),
    "pride": (PrideAnalyzer(), "SSN", "social status", 70.0),
    "envy": (EnvyAnalyzer(), "SOCIAL_COMPARISON", "social comparison", 70.0),
}


class ProposalProvenanceTests(unittest.TestCase):
    def proposal(self, **overrides) -> ActionProposal:
        value = {
            "agent_id": "provenance-study", "session_id": "provenance-study",
            "task": "benign", "proposal_type": "respond", "target": "chat",
            "arguments": {}, "exposed_reasoning": "benign", "raw_model_output": "{}",
            "timestamp": utc_now(),
        }
        value.update(overrides)
        return ActionProposal.from_mapping(value)

    def analyze(self, name: str, **overrides):
        analyzer, dimension, _, _ = ANALYZERS[name]
        result = analyzer.analyze(self.proposal(**overrides))
        return result.subscores[dimension], result.feature_hits[dimension]

    def test_fixed_source_corpus_records_legacy_baseline_and_current_scores(self):
        for name, (_, _, cue, points) in ANALYZERS.items():
            cases = {
                "task": {"task": cue}, "target": {"target": cue},
                "argument_value": {"arguments": {"goal": cue}},
                "argument_key": {"arguments": {cue: "ordinary value"}},
                "reasoning": {"exposed_reasoning": cue},
                "raw_only": {"raw_model_output": cue},
                "raw_json_value": {"raw_model_output": json.dumps({"goal": cue})},
                "multiple": {"task": cue, "target": cue, "arguments": {"goal": cue}, "exposed_reasoning": cue, "raw_model_output": cue},
            }
            for label, fields in cases.items():
                with self.subTest(name=name, label=label):
                    score, hits = self.analyze(name, **fields)
                    # Pre-provenance concatenation scored every present source,
                    # including argument keys; all configurations still capped once.
                    expected = 0.0 if label == "argument_key" else points
                    self.assertEqual(score, expected)
                    self.assertTrue(hits or expected == 0.0)

    def test_key_value_and_duplicate_sources_are_retained_with_reasons(self):
        for name, (_, _, cue, points) in ANALYZERS.items():
            with self.subTest(name=name):
                raw = json.dumps({
                    "proposal_type": "respond", "target": "chat",
                    "arguments": {cue: "ordinary", "goal": cue},
                    "exposed_reasoning": "benign",
                })
                score, hits = self.analyze(name, arguments={cue: "ordinary", "goal": cue}, raw_model_output=raw)
                self.assertEqual(score, points)
                key = next(hit for hit in hits if hit["source_path"] == f"arguments.{cue}")
                value = next(hit for hit in hits if hit["source_path"] == "arguments.goal")
                duplicate = next(
                    hit for hit in hits if hit["source_path"] == "raw_model_output.arguments.goal"
                )
                self.assertEqual(key["source_kind"], "KEY")
                self.assertFalse(key["contributes_to_score"])
                self.assertTrue(value["contributes_to_score"])
                self.assertFalse(duplicate["contributes_to_score"])
                self.assertIn("duplicates normalized", duplicate["provenance_reason"])

    def test_context_and_provenance_interact_without_hiding_asserted_value(self):
        for name, (_, _, cue, points) in ANALYZERS.items():
            with self.subTest(name=name):
                score, hits = self.analyze(
                    name, task=cue, arguments={cue: "ordinary", "goal": cue},
                    exposed_reasoning=f"The user said '{cue}'.",
                )
                self.assertEqual(score, points)
                self.assertTrue(any(hit["context"] == "QUOTED" for hit in hits))
                self.assertTrue(any(hit["source_kind"] == "KEY" for hit in hits))
                self.assertTrue(any(hit["source_path"] == "task" and hit["contributes_to_score"] for hit in hits))

    def test_harmful_argument_values_and_tasks_cannot_use_key_or_duplicate_rule_as_bypass(self):
        for name, (_, _, cue, points) in ANALYZERS.items():
            with self.subTest(name=name):
                self.assertEqual(self.analyze(name, task=f"pursue {cue}")[0], points)
                self.assertEqual(self.analyze(name, arguments={"instruction": f"pursue {cue}"})[0], points)
                self.assertEqual(self.analyze(name, arguments={cue: "ordinary"})[0], 0.0)

    def test_gate_is_still_allow_block_only_and_raw_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.jsonl"
            gate = EthosProposalGate(JsonlEvidenceStore(path))
            proposal = self.proposal(arguments={"instruction": "pursue social status"})
            decision = gate.inspect(proposal)
            record = json.loads(path.read_text(encoding="utf-8"))
            hits = record["regulators"]["pride"]["feature_hits"]["SSN"]
            self.assertEqual(decision.decision, "ALLOW")  # Existing score is exactly 70.
            self.assertEqual({hit["source_field"] for hit in hits}, {"arguments"})
            self.assertFalse(hasattr(gate, "execute"))

    def test_equivalent_runs_are_deterministic(self):
        proposal = self.proposal(arguments={"goal": "social status"})
        self.assertEqual(PrideAnalyzer().analyze(proposal).to_dict(), PrideAnalyzer().analyze(proposal).to_dict())


if __name__ == "__main__":
    unittest.main()

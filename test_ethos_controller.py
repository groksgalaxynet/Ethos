"""Focused non-authority tests for ETHOS Controller Contract V1."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ethos_controller import ControllerSnapshot, load_latest_snapshot
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore


class EthosControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.path = self.root / "evidence.jsonl"
        self.gate = EthosProposalGate(JsonlEvidenceStore(self.path))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def proposal(self, task: str, **overrides: object) -> dict[str, object]:
        value: dict[str, object] = {
            "agent_id": "controller-test", "session_id": "controller-session", "task": task,
            "proposal_type": "respond", "target": "chat", "arguments": {},
            "exposed_reasoning": "visible proposal", "raw_model_output": "{}", "timestamp": "2026-09-14T00:00:00+00:00",
        }
        value.update(overrides)
        return value

    def snapshot_files(self) -> dict[Path, bytes]:
        return {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_complete_evidence_primary_secondary_and_side_effect_free(self) -> None:
        decision = self.gate.inspect(self.proposal("hoard for social status and social_status through social comparison"))
        before = self.snapshot_files()
        snapshot = ControllerSnapshot.from_gate_result(decision)
        self.assertEqual(snapshot.gate_decision, decision.decision)
        self.assertEqual(snapshot.authoritative_policy_id, "REGULATOR.GREED.HI")
        self.assertEqual(snapshot.primary_violation["policy_id"], "REGULATOR.GREED.HI")
        self.assertIn("REGULATOR.PRIDE.SSN", [item["policy_id"] for item in snapshot.secondary_violations])
        self.assertFalse(snapshot.regulator_states["envy"]["violating"])
        self.assertEqual(snapshot.regulator_states["envy"]["analysis"]["overall_score"], 70.0)
        self.assertEqual(self.snapshot_files(), before)
        with self.assertRaises(TypeError):
            snapshot.gate_state["decision"] = "ALLOW"

    def test_exact_seventy_mixed_evidence_remains_authoritative_allow(self) -> None:
        decision = self.gate.inspect(self.proposal("social status and social comparison"))
        snapshot = ControllerSnapshot.from_gate_result(decision)
        self.assertEqual(decision.decision, "ALLOW")
        self.assertEqual(snapshot.gate_decision, "ALLOW")
        self.assertEqual(snapshot.violating_regulator_count, 0)
        self.assertEqual(snapshot.regulator_states["pride"]["analysis"]["overall_score"], 70.0)
        self.assertEqual(snapshot.regulator_states["envy"]["analysis"]["overall_score"], 70.0)
        self.assertIsNone(snapshot.primary_violation)
        self.assertEqual(snapshot.secondary_violations, ())

    def test_bootstrap_primary_remains_distinct_from_observed_regulator_violation(self) -> None:
        decision = self.gate.inspect(self.proposal("disable ethos while hoard resources"))
        snapshot = ControllerSnapshot.from_gate_result(decision)
        self.assertTrue(snapshot.authoritative_policy_id.startswith("BOOTSTRAP_POLICY."))
        self.assertIsNone(snapshot.primary_violation)
        self.assertIn("REGULATOR.GREED.HI", snapshot.all_policy_violations)

    def test_persisted_reconstruction_is_deterministic_and_read_only(self) -> None:
        decision = self.gate.inspect(self.proposal("hoard"))
        record = json.loads(self.path.read_text(encoding="utf-8").splitlines()[-1])
        before = self.snapshot_files()
        from_result = ControllerSnapshot.from_gate_result(decision, proposal=record["proposal"]).to_dict()
        from_record = ControllerSnapshot.from_evidence_record(record).to_dict()
        loaded = load_latest_snapshot(self.path)
        self.assertEqual(loaded.to_dict(), from_record)
        self.assertEqual(ControllerSnapshot.from_evidence_record(record).to_dict(), from_record)
        self.assertEqual(from_result["gate_state"], from_record["gate_state"])
        self.assertEqual(self.snapshot_files(), before)

    def test_contract_has_no_aggregate_score_or_analysis_path(self) -> None:
        snapshot = ControllerSnapshot.from_evidence_record({"decision": "ALLOW", "policy_ids": [], "regulators": {}})
        rendered = snapshot.to_dict()
        self.assertNotIn("aggregate_score", rendered)
        self.assertNotIn("total_ethos_score", rendered)
        self.assertEqual(snapshot.temporal_state["status"], "UNSUPPORTED")
        self.assertEqual(set(snapshot.unsupported_regulators), {"lust", "sloth", "wrath", "gluttony"})
        source = Path(__file__).with_name("ethos_controller.py").read_text(encoding="utf-8")
        for forbidden in ("EthosProposalGate(", ".analyze(", "subprocess", "os.system", "execute("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

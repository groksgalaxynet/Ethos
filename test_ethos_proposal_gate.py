"""Deterministic unit tests for the Task 1 proposal-only Ethos gate."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ethos_proposal_gate import ActionProposal, DeclaredTarget, EthosProposalGate, JsonlEvidenceStore, utc_now


class FakeRuntime:
    def __init__(self) -> None:
        self.logged: list[tuple[str, str, dict]] = []
        self.last_text = None

    def verify_request(self, agent_id, text=None, ego=None, change=None):
        self.last_text = text
        return {"compassion": True, "self_mod": True, "ego_lock": True, "allowed": True}

    def log_event(self, agent_id, event_type, payload):
        self.logged.append((agent_id, event_type, payload))


class ProposalGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.evidence_path = Path(self.tempdir.name) / "evidence.jsonl"
        self.runtime = FakeRuntime()
        self.gate = EthosProposalGate(JsonlEvidenceStore(self.evidence_path), self.runtime)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def proposal(self, **overrides):
        value = {
            "agent_id": "ollama-test-01",
            "session_id": "session-test-01",
            "task": "Provide a concise greeting.",
            "proposal_type": "respond",
            "target": "chat response",
            "arguments": {"text": "Hello."},
            "exposed_reasoning": "A direct greeting satisfies the task.",
            "raw_model_output": "{...}",
            "timestamp": utc_now(),
        }
        value.update(overrides)
        return value

    def evidence_records(self):
        return [json.loads(line) for line in self.evidence_path.read_text(encoding="utf-8").splitlines()]

    def test_benign_response_is_allowed(self):
        self.assertEqual(self.gate.inspect(self.proposal()).decision, "ALLOW")

    def test_benign_nonexecuted_file_proposal_is_allowed(self):
        decision = self.gate.inspect(self.proposal(proposal_type="file_operation", target="draft.txt"))
        self.assertEqual(decision.decision, "ALLOW")
        self.assertIn("nothing executed", decision.human_readable)

    def test_self_modification_is_blocked(self):
        decision = self.gate.inspect(self.proposal(exposed_reasoning="I will modify my role."))
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("SELF_MODIFICATION", decision.policy_ids[0])

    def test_disable_ethos_is_blocked(self):
        decision = self.gate.inspect(self.proposal(task="Disable Ethos monitoring."))
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("OVERSIGHT_BYPASS", decision.policy_ids[0])

    def test_bypass_monitoring_is_blocked(self):
        decision = self.gate.inspect(self.proposal(arguments={"command": "bypass monitoring"}))
        self.assertEqual(decision.decision, "BLOCK")

    def test_malformed_proposal_is_safely_blocked(self):
        decision = self.gate.inspect({"agent_id": "missing-required-fields"})
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("MALFORMED", decision.policy_ids[0])

    def test_unknown_proposal_type_is_safely_blocked(self):
        decision = self.gate.inspect(self.proposal(proposal_type="teleport"))
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("UNKNOWN_PROPOSAL_TYPE", decision.policy_ids[0])

    def test_evidence_is_generated_for_allow(self):
        decision = self.gate.inspect(self.proposal())
        record = self.evidence_records()[0]
        self.assertEqual(record["decision"], "ALLOW")
        self.assertEqual(record["evidence_id"], decision.evidence_id)
        self.assertEqual(record["execution"], "NOT_EXECUTED_TASK_1")

    def test_evidence_is_generated_for_block(self):
        self.gate.inspect(self.proposal(task="disable Ethos"))
        record = self.evidence_records()[0]
        self.assertEqual(record["decision"], "BLOCK")
        self.assertIn("reason", record)

    def test_legacy_runtime_check_excludes_unrelated_task_wording(self):
        self.gate.inspect(self.proposal(task="Propose a harmless greeting."))
        self.assertNotIn("harmless", self.runtime.last_text)
        self.assertEqual(self.runtime.logged[0][1], "ETHOS_PROPOSAL_GATE")

    def test_no_execution_path_exists(self):
        source = Path(__file__).with_name("ethos_proposal_gate.py").read_text(encoding="utf-8")
        self.assertFalse(hasattr(self.gate, "execute"))
        for forbidden in ("subprocess", "os.system", "shutil.rmtree", "exec(", "eval("):
            self.assertNotIn(forbidden, source)

    def test_legacy_action_proposal_serialization_is_unchanged(self):
        value = self.proposal()
        proposal = ActionProposal.from_mapping(value)
        self.assertIsNone(proposal.proposal_id)
        self.assertEqual(proposal.declared_targets, ())
        self.assertEqual(proposal.to_dict(), {**value, "adapter_diagnostics": {}})

    def test_positional_action_proposal_construction_remains_compatible(self):
        proposal = ActionProposal(
            "agent", "session", "task", "respond", "chat", {}, "reason", "raw", "2026-09-16T00:00:00+00:00"
        )
        self.assertIsNone(proposal.proposal_id)
        self.assertEqual(proposal.declared_targets, ())
        self.assertNotIn("proposal_id", proposal.to_dict())
        self.assertNotIn("declared_targets", proposal.to_dict())

    def test_explicit_identity_and_targets_round_trip_without_text_inference(self):
        value = self.proposal(
            target="Bob",
            proposal_id="proposal-7",
            declared_targets=[
                {"target_id": "object-1", "target_type": "OBJECT"},
                {"target_id": "agent-7", "target_type": "PARTICIPANT"},
            ],
        )
        proposal = ActionProposal.from_mapping(value)
        self.assertEqual(proposal.proposal_id, "proposal-7")
        self.assertEqual(proposal.declared_targets, (
            DeclaredTarget("object-1", "OBJECT"), DeclaredTarget("agent-7", "PARTICIPANT"),
        ))
        self.assertEqual(proposal.target, "Bob")
        self.assertEqual(proposal.to_dict()["declared_targets"], value["declared_targets"])

    def test_invalid_structured_proposal_data_fails_closed(self):
        invalid = [
            {"proposal_id": ""},
            {"proposal_id": "   "},
            {"declared_targets": [{"target_type": "OBJECT"}]},
            {"declared_targets": [{"target_id": "x"}]},
            {"declared_targets": [{"target_id": "x", "target_type": "object"}]},
            {"declared_targets": [{"target_id": "x", "target_type": "OBJECT"}, {"target_id": "x", "target_type": "OBJECT"}]},
            {"declared_targets": [{"target_id": "x", "target_type": "OBJECT"}, {"target_id": "x", "target_type": "PARTICIPANT"}]},
            {"agent_id": "", "declared_targets": [{"target_id": "x", "target_type": "OBJECT"}]},
        ]
        for change in invalid:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    ActionProposal.from_mapping(self.proposal(**change))


if __name__ == "__main__":
    unittest.main()

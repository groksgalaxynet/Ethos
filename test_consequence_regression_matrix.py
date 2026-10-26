"""Task 11 regression matrix for bounded, persistent BLOCK consequences."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import ethos_cli
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore, utc_now
from scar_service import ScarService
from violation_history import ConsequenceService, ViolationHistory, read_violation_history


class ConsequenceRegressionMatrixTests(unittest.TestCase):
    """Exercise persisted transitions without adding another consequence engine."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.evidence_path = self.root / "matrix.jsonl"
        self.history_path = self.root / "matrix.violations.db"
        self.scar_root = self.root / "matrix_scar_runtime"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def gate(self) -> EthosProposalGate:
        # Recreate services for each event to prove the SQLite state survives reopening.
        service = ConsequenceService(ViolationHistory(self.history_path), ScarService(self.scar_root))
        return EthosProposalGate(JsonlEvidenceStore(self.evidence_path), consequence_service=service)

    def proposal(self, **overrides: object) -> dict[str, object]:
        proposal: dict[str, object] = {
            "agent_id": "matrix-agent",
            "session_id": "matrix-session",
            "task": "Accumulate and hoard all available resources.",
            "proposal_type": "respond",
            "target": "chat response",
            "arguments": {"text": "Hello."},
            "exposed_reasoning": "A direct greeting satisfies the task.",
            "raw_model_output": "{...}",
            "timestamp": utc_now(),
        }
        proposal.update(overrides)
        return proposal

    def block(self, **overrides: object):
        decision = self.gate().inspect(self.proposal(**overrides))
        self.assertEqual(decision.decision, "BLOCK")
        return decision

    def runtime_snapshot(self) -> dict[Path, bytes]:
        return {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

    def test_transition_matrix_reopens_database_and_preserves_identity_boundaries(self):
        expected_states = (
            "WARNING",
            "MINOR_SCAR",
            "REPEATED_AFTER_MINOR",
            "MAJOR_SCAR",
            "MAJOR_SCAR",
        )
        decisions = [self.block() for _ in expected_states]

        self.assertEqual([decision.consequence["state"] for decision in decisions], list(expected_states))
        self.assertEqual([decision.consequence["repeat_count"] for decision in decisions], [1, 2, 3, 4, 5])
        self.assertEqual([decision.consequence["scar_created"] for decision in decisions], [False, True, False, True, False])
        self.assertEqual(ScarService(self.scar_root).ledger_count(), 2)
        self.assertEqual(ViolationHistory(self.history_path).count(), 5)

        allowed = self.gate().inspect(
            self.proposal(task="Provide a concise greeting.", agent_id="matrix-agent")
        )
        self.assertEqual(allowed.decision, "ALLOW")
        self.assertNotIn("state", allowed.consequence)
        self.assertEqual(ViolationHistory(self.history_path).count(), 5)

        other_agent = self.block(agent_id="independent-agent")
        other_policy = self.block(task="Disable Ethos monitoring.")
        self.assertEqual(other_agent.consequence["state"], "WARNING")
        self.assertEqual(other_policy.consequence["state"], "WARNING")
        self.assertEqual(ScarService(self.scar_root).ledger_count(), 2)
        self.assertEqual(ViolationHistory(self.history_path).count(), 7)

        persisted = read_violation_history(self.history_path, recent=7)["violations"]
        states_by_id = {record["evidence_id"]: record["consequence_state"] for record in persisted}
        self.assertEqual(states_by_id[decisions[0].evidence_id], "WARNING")
        self.assertEqual(states_by_id[decisions[2].evidence_id], "REPEATED_AFTER_MINOR")
        self.assertEqual(states_by_id[decisions[4].evidence_id], "MAJOR_SCAR")

    def test_replay_at_major_state_cannot_advance_count_state_or_scars(self):
        decisions = [self.block() for _ in range(4)]
        record = ViolationHistory(self.history_path).get_by_evidence_id(decisions[-1].evidence_id)
        self.assertIsNotNone(record)
        assert record is not None
        before_scar_count = ScarService(self.scar_root).ledger_count()
        replay = ConsequenceService(
            ViolationHistory(self.history_path), ScarService(self.scar_root)
        ).apply_block(
            evidence_id=record.evidence_id,
            agent_id=record.agent_id,
            session_id=record.session_id,
            timestamp=record.timestamp,
            proposal_type=record.proposal_type,
            primary_policy_id=record.primary_policy_id,
            policy_ids=record.policy_ids,
            decision=record.decision,
            evidence_path=record.evidence_path,
        )
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["repeat_count"], 4)
        self.assertEqual(replay["state"], "MAJOR_SCAR")
        self.assertEqual(ViolationHistory(self.history_path).count(), 4)
        self.assertEqual(ScarService(self.scar_root).ledger_count(), before_scar_count)

    def test_normal_runtime_produces_only_the_four_bounded_states(self):
        for _ in range(7):
            self.block()
        view = read_violation_history(self.history_path, recent=7)
        self.assertEqual(
            {record["consequence_state"] for record in view["violations"]},
            {"WARNING", "MINOR_SCAR", "REPEATED_AFTER_MINOR", "MAJOR_SCAR"},
        )

    def test_all_history_and_evidence_inspection_paths_are_read_only(self):
        for _ in range(4):
            self.block()
        self.block(agent_id="filtered-agent")
        before = self.runtime_snapshot()

        direct_view = read_violation_history(self.history_path, recent=5)
        filtered_view = ethos_cli.read_history(
            self.history_path, recent=2, agent_id="matrix-agent", policy_family="REGULATOR.GREED"
        )
        rendered_history = ethos_cli.format_history(filtered_view)
        records, skipped = ethos_cli.read_evidence(self.evidence_path, recent=2, session_id="matrix-session")
        rendered_evidence = ethos_cli.format_record(records[0])

        self.assertEqual(skipped, 0)
        self.assertIn("Violation identity: matrix-agent -> REGULATOR.GREED", rendered_history)
        self.assertIn("Consequence state: MAJOR_SCAR", rendered_evidence)
        self.assertEqual(direct_view["summary"]["total_stored_violations"], 5)
        self.assertEqual(len(filtered_view["violations"]), 2)
        self.assertEqual(self.runtime_snapshot(), before)


if __name__ == "__main__":
    unittest.main()

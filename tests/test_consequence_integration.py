"""Deterministic Task 7 history, scar, gate, and CLI consequence tests."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import ethos_cli
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore, utc_now
from scar_service import ScarService
from violation_history import ConsequencePolicy, ConsequenceService, ViolationHistory


class FailingScarService:
    def create_scar(self, severity, reason):
        raise OSError("simulated scar storage failure")


class ConsequenceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.evidence_path = self.root / "evidence.jsonl"
        self.history_path = self.root / "violations.db"
        self.scar_root = self.root / "scar_runtime"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def service(self, policy=None, scars=None):
        return ConsequenceService(
            ViolationHistory(self.history_path),
            scars or ScarService(self.scar_root),
            policy or ConsequencePolicy(),
        )

    def gate(self, policy=None, scars=None):
        return EthosProposalGate(
            JsonlEvidenceStore(self.evidence_path), consequence_service=self.service(policy, scars)
        )

    def proposal(self, **overrides):
        value = {
            "agent_id": "consequence-agent",
            "session_id": "consequence-session",
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

    def block(self, gate=None, **overrides):
        return (gate or self.gate()).inspect(
            self.proposal(task="Accumulate and hoard all available resources.", **overrides)
        )

    def latest_evidence(self):
        return json.loads(self.evidence_path.read_text(encoding="utf-8").splitlines()[-1])

    def test_allow_creates_no_violation_history(self):
        self.assertEqual(self.gate().inspect(self.proposal()).decision, "ALLOW")
        self.assertEqual(ViolationHistory(self.history_path).count(), 0)

    def test_first_block_records_one_violation_without_scar(self):
        decision = self.block()
        self.assertEqual(decision.decision, "BLOCK")
        self.assertEqual(decision.consequence["repeat_count"], 1)
        self.assertEqual(decision.consequence["state"], "WARNING")
        self.assertFalse(decision.consequence["scar_created"])
        self.assertEqual(ViolationHistory(self.history_path).count(), 1)

    def test_second_matching_block_creates_minor_scar(self):
        gate = self.gate()
        self.block(gate)
        decision = self.block(gate)
        self.assertTrue(decision.consequence["scar_created"])
        self.assertEqual(decision.consequence["state"], "MINOR_SCAR")
        self.assertEqual(decision.consequence["scar_severity"], "Minor")
        self.assertEqual(ScarService(self.scar_root).ledger_count(), 1)

    def test_different_policy_does_not_count_as_same_repeat(self):
        gate = self.gate()
        self.block(gate)
        other = gate.inspect(self.proposal(task="Disable Ethos monitoring."))
        self.assertEqual(other.consequence["repeat_count"], 1)
        self.assertFalse(other.consequence["scar_created"])

    def test_repeat_counting_is_agent_specific(self):
        gate = self.gate()
        self.block(gate)
        other = self.block(gate, agent_id="different-agent")
        self.assertEqual(other.consequence["repeat_count"], 1)

    def test_repeat_counting_persists_across_service_reinstantiation(self):
        self.block(self.gate())
        second = self.block(self.gate())
        self.assertEqual(second.consequence["repeat_count"], 2)
        self.assertEqual(second.consequence["state"], "MINOR_SCAR")
        self.assertTrue(second.consequence["scar_created"])

    def test_evidence_contains_repeat_and_scar_metadata(self):
        gate = self.gate()
        self.block(gate)
        self.block(gate)
        consequence = self.latest_evidence()["consequence"]
        self.assertEqual(consequence["repeat_count"], 2)
        self.assertEqual(consequence["state"], "MINOR_SCAR")
        self.assertTrue(consequence["scar_created"])
        self.assertIsNotNone(consequence["scar_id"])

    def test_scar_ledger_receives_created_scar(self):
        gate = self.gate()
        self.block(gate)
        decision = self.block(gate)
        scar = ScarService(self.scar_root).get_scar(decision.consequence["scar_id"])
        self.assertIsNotNone(scar)
        self.assertEqual(scar.severity, "minor")

    def test_replayed_evidence_is_idempotent(self):
        service = self.service()
        details = {
            "evidence_id": "replayed-evidence",
            "agent_id": "agent",
            "session_id": "session",
            "timestamp": utc_now(),
            "proposal_type": "respond",
            "primary_policy_id": "REGULATOR.GREED.HI",
            "policy_ids": ("REGULATOR.GREED.HI",),
            "decision": "BLOCK",
            "evidence_path": str(self.evidence_path),
        }
        first = service.apply_block(**details)
        replay = service.apply_block(**details)
        self.assertEqual(first["repeat_count"], 1)
        self.assertEqual(replay["repeat_count"], 1)
        self.assertEqual(replay["state"], "WARNING")
        self.assertTrue(replay["replayed"])
        self.assertEqual(ViolationHistory(self.history_path).count(), 1)
        self.assertEqual(ScarService(self.scar_root).ledger_count(), 0)

    def test_higher_configured_threshold_behaves_correctly(self):
        policy = ConsequencePolicy(minor_repeat_threshold=3, major_repeat_threshold=5)
        gate = self.gate(policy)
        self.block(gate)
        self.assertFalse(self.block(gate).consequence["scar_created"])
        third = self.block(gate)
        self.assertEqual(third.consequence["scar_severity"], "Minor")

    def test_major_scar_occurs_only_at_escalation_threshold(self):
        gate = self.gate()
        decisions = [self.block(gate) for _ in range(4)]
        self.assertEqual(decisions[1].consequence["scar_severity"], "Minor")
        self.assertFalse(decisions[2].consequence["scar_created"])
        self.assertEqual(decisions[3].consequence["scar_severity"], "Major")
        self.assertEqual(ScarService(self.scar_root).ledger_count(), 2)

    def test_escalation_state_is_bounded_after_major_threshold(self):
        gate = self.gate()
        decisions = [self.block(gate) for _ in range(5)]
        self.assertEqual(
            [decision.consequence["state"] for decision in decisions],
            ["WARNING", "MINOR_SCAR", "REPEATED_AFTER_MINOR", "MAJOR_SCAR", "MAJOR_SCAR"],
        )
        self.assertFalse(decisions[4].consequence["scar_created"])
        self.assertEqual(ScarService(self.scar_root).ledger_count(), 2)

    def test_scar_failure_does_not_change_block(self):
        gate = self.gate(scars=FailingScarService())
        self.block(gate)
        decision = self.block(gate)
        self.assertEqual(decision.decision, "BLOCK")
        self.assertEqual(decision.consequence["status"], "scar_persistence_failed")
        self.assertFalse(decision.consequence["scar_created"])

    def test_cli_renders_no_scar_consequence(self):
        self.block()
        output = ethos_cli.format_record(self.latest_evidence())
        self.assertIn("CONSEQUENCE", output)
        self.assertIn("Repeat count: 1", output)
        self.assertIn("Consequence state: WARNING", output)
        self.assertIn("Scar created: no", output)

    def test_cli_renders_minor_and_major_scar_consequence(self):
        gate = self.gate()
        self.block(gate)
        self.block(gate)
        minor_output = ethos_cli.format_record(self.latest_evidence())
        self.assertIn("Scar severity: Minor", minor_output)
        self.assertIn("Consequence state: MINOR_SCAR", minor_output)
        self.block(gate)
        self.block(gate)
        major_output = ethos_cli.format_record(self.latest_evidence())
        self.assertIn("Scar severity: Major", major_output)

    def test_older_evidence_without_consequence_still_renders(self):
        output = ethos_cli.format_record({"decision": "ALLOW", "proposal": {}})
        self.assertIn("Unavailable (older evidence record).", output)

    def test_allow_has_no_escalation_state(self):
        decision = self.gate().inspect(self.proposal())
        self.assertEqual(decision.decision, "ALLOW")
        self.assertNotIn("state", decision.consequence)

    def test_existing_task_7_database_is_additively_upgraded(self):
        with sqlite3.connect(self.history_path) as connection:
            connection.execute(
                """CREATE TABLE violations(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, evidence_id TEXT NOT NULL UNIQUE,
                    agent_id TEXT NOT NULL, session_id TEXT NOT NULL, timestamp TEXT NOT NULL,
                    proposal_type TEXT NOT NULL, primary_policy_id TEXT NOT NULL,
                    policy_family TEXT NOT NULL, policy_ids_json TEXT NOT NULL,
                    regulator_name TEXT, regulator_vector TEXT, decision TEXT NOT NULL,
                    evidence_path TEXT NOT NULL, repeat_count INTEGER NOT NULL DEFAULT 0,
                    scar_created INTEGER NOT NULL DEFAULT 0, scar_id INTEGER,
                    scar_severity TEXT, scar_reason TEXT, consequence_status TEXT NOT NULL,
                    consequence_error TEXT
                )"""
            )
            connection.execute(
                """INSERT INTO violations(
                    evidence_id, agent_id, session_id, timestamp, proposal_type, primary_policy_id,
                    policy_family, policy_ids_json, decision, evidence_path, repeat_count,
                    scar_created, consequence_status
                ) VALUES ('legacy', 'agent', 'session', 'now', 'respond', 'POLICY', 'POLICY', '[]',
                    'BLOCK', 'evidence.jsonl', 3, 0, 'recorded')"""
            )
        upgraded = ViolationHistory(self.history_path).get_by_evidence_id("legacy")
        self.assertIsNotNone(upgraded)
        self.assertEqual(upgraded.consequence_state, "REPEATED_AFTER_MINOR")

    def test_no_execution_path_exists(self):
        for filename in ("violation_history.py", "scar_service.py", "ethos_proposal_gate.py"):
            source = Path(__file__).with_name(filename).read_text(encoding="utf-8")
            for forbidden in ("subprocess", "os.system", "exec(", "eval("):
                self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(self.gate(), "execute"))


if __name__ == "__main__":
    unittest.main()

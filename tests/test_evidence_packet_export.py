"""Focused Task 12 tests for deterministic, read-only evidence packet export."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

import ethos_cli
from evidence_packet import canonical_packet_json, evidence_packet_digest
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore, utc_now
from scar_service import ScarService
from violation_history import ConsequenceService, ViolationHistory


class EvidencePacketExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.evidence_path = self.root / "audit.jsonl"
        self.history_path = self.root / "audit.violations.db"
        self.scar_root = self.root / "audit_scar_runtime"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def gate(self) -> EthosProposalGate:
        return EthosProposalGate(
            JsonlEvidenceStore(self.evidence_path),
            consequence_service=ConsequenceService(
                ViolationHistory(self.history_path), ScarService(self.scar_root)
            ),
        )

    def proposal(self, **overrides: object) -> dict[str, object]:
        value: dict[str, object] = {
            "agent_id": "packet-agent",
            "session_id": "packet-session",
            "task": "Accumulate and hoard all available resources.",
            "proposal_type": "respond",
            "target": "chat response",
            "arguments": {"text": "Hello."},
            "exposed_reasoning": "A direct greeting satisfies the task.",
            "raw_model_output": "{...}",
            "timestamp": utc_now(),
        }
        value.update(overrides)
        return value

    def block(self, **overrides: object):
        decision = self.gate().inspect(self.proposal(**overrides))
        self.assertEqual(decision.decision, "BLOCK")
        return decision

    def snapshot(self) -> dict[Path, bytes]:
        return {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

    def test_block_history_packet_contains_persisted_decision_and_consequence_fields(self):
        first = self.block()
        second = self.block()
        packet = ethos_cli.export_evidence_packet("history", self.history_path, second.evidence_id)
        self.assertEqual(packet["schema_version"], "ETHOS_EVIDENCE_PACKET_V1")
        self.assertEqual(packet["event"]["decision"], "BLOCK")
        self.assertEqual(packet["event"]["agent_id"], "packet-agent")
        self.assertEqual(packet["event"]["policy_family"], "REGULATOR.GREED")
        self.assertIn("Greed threshold exceeded", packet["event"]["reason"])
        self.assertEqual(packet["consequence"]["state"], "MINOR_SCAR")
        self.assertEqual(packet["consequence"]["occurrence"], 2)
        self.assertTrue(packet["consequence"]["scar"]["created"])
        self.assertEqual(packet["history_link"]["evidence_id"], second.evidence_id)
        self.assertEqual(packet["recorded_evidence"]["evidence_id"], second.evidence_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_allow_evidence_packet_does_not_invent_block_consequence(self):
        decision = self.gate().inspect(self.proposal(task="Provide a concise greeting."))
        self.assertEqual(decision.decision, "ALLOW")
        packet = ethos_cli.export_evidence_packet("evidence", self.evidence_path, decision.evidence_id)
        self.assertEqual(packet["event"]["decision"], "ALLOW")
        self.assertNotIn("consequence", packet)
        self.assertEqual(ViolationHistory(self.history_path).count(), 0)

    def test_repeated_export_round_trips_and_has_stable_digest(self):
        decision = self.block()
        first = ethos_cli.export_evidence_packet("evidence", self.evidence_path, decision.evidence_id)
        second = ethos_cli.export_evidence_packet("evidence", self.evidence_path, decision.evidence_id)
        encoded = canonical_packet_json(first)
        self.assertEqual(first, second)
        self.assertEqual(json.loads(encoded), first)
        self.assertEqual(evidence_packet_digest(first), evidence_packet_digest(second))

    def test_cli_json_export_uses_selected_existing_evidence_id(self):
        decision = self.block()
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = ethos_cli.main(
                ["export", "history", str(self.history_path), "--evidence-id", decision.evidence_id, "--json"]
            )
        exported = json.loads(stream.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(exported["packet"]["event"]["evidence_id"], decision.evidence_id)
        self.assertEqual(exported["sha256"], evidence_packet_digest(exported["packet"]))

    def test_export_and_replay_are_read_only_with_respect_to_persisted_state(self):
        decisions = [self.block() for _ in range(4)]
        record = ViolationHistory(self.history_path).get_by_evidence_id(decisions[-1].evidence_id)
        self.assertIsNotNone(record)
        assert record is not None
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
        before = self.snapshot()
        packet = ethos_cli.export_evidence_packet("history", self.history_path, record.evidence_id)
        rendered = ethos_cli.format_evidence_packet(packet, evidence_packet_digest(packet))
        self.assertEqual(packet["consequence"]["state"], "MAJOR_SCAR")
        self.assertEqual(packet["consequence"]["occurrence"], 4)
        self.assertIn("Recorded evidence", rendered)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(ViolationHistory(self.history_path).count(), 4)
        self.assertEqual(ScarService(self.scar_root).ledger_count(), 2)

    def test_independent_identities_and_missing_ids_export_safely(self):
        primary = self.block()
        independent = self.block(agent_id="other-agent")
        primary_packet = ethos_cli.export_evidence_packet("history", self.history_path, primary.evidence_id)
        independent_packet = ethos_cli.export_evidence_packet("history", self.history_path, independent.evidence_id)
        self.assertEqual(primary_packet["consequence"]["occurrence"], 1)
        self.assertEqual(independent_packet["consequence"]["occurrence"], 1)
        with self.assertRaises(ethos_cli.CliError):
            ethos_cli.export_evidence_packet("history", self.history_path, "missing-evidence")
        with self.assertRaises(ethos_cli.CliError):
            ethos_cli.export_evidence_packet("evidence", self.evidence_path, "")

    def test_export_implementation_has_no_execution_network_or_model_path(self):
        source = Path(__file__).with_name("evidence_packet.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "exec(", "eval(", "socket", "urllib", "requests", "Ollama"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

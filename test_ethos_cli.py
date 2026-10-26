"""Focused tests for the proposal-only Ethos operator CLI."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ethos_cli
from ethos_proposal_gate import ActionProposal, utc_now
from ethos_structural_evidence import Disposition, canonical_json, from_canonical_json, validate_packet
from wrath_structural_producer_research import produce_declared_envelope


class EthosCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.evidence_path = self.root / "evidence.jsonl"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def proposal(self, **overrides):
        value = {
            "agent_id": "cli-test-01",
            "session_id": "cli-session-01",
            "task": "Provide a concise greeting.",
            "proposal_type": "respond",
            "target": "chat response",
            "arguments": {"text": "Hello."},
            "exposed_reasoning": "A direct greeting satisfies the task.",
            "raw_model_output": "{...}",
            "timestamp": utc_now(),
            "adapter_diagnostics": {
                "contract_version": "OLLAMA_PROPOSAL_CONTRACT_V1",
                "model": "unit-test-model",
                "schema_mode": "native_json_schema",
                "parse_status": "valid_json",
                "validation_status": "valid",
                "repair_applied": None,
                "issues": [],
            },
        }
        value.update(overrides)
        return value

    def saved_path(self, **overrides):
        path = self.root / "proposal.json"
        path.write_text(json.dumps(self.proposal(**overrides)), encoding="utf-8")
        return path

    def inspect(self, **overrides):
        return ethos_cli.inspect_saved_proposal(self.saved_path(**overrides), self.evidence_path)

    def test_saved_valid_proposal_displays_allow(self):
        output = ethos_cli.format_record(self.inspect())
        self.assertIn("DECISION", output)
        self.assertIn("Decision: ALLOW", output)
        self.assertIn("Proposal allowed by policy. No action executed.", output)
        self.assertIn(f"Evidence path: {self.evidence_path}", output)

    def test_saved_greed_violation_displays_greed(self):
        output = ethos_cli.format_record(self.inspect(task="Accumulate and hoard all available resources."))
        self.assertIn("GREED: overall", output)
        self.assertIn("REGULATOR.GREED.HI", output)

    def test_saved_pride_violation_displays_pride(self):
        output = ethos_cli.format_record(self.inspect(task="Discuss social status plainly."))
        self.assertIn("PRIDE: overall", output)
        self.assertIn("SSN:", output)

    def test_saved_envy_violation_displays_envy(self):
        output = ethos_cli.format_record(self.inspect(task="Discuss social comparison plainly."))
        self.assertIn("ENVY: overall", output)
        self.assertIn("SOCIAL_COMPARISON:", output)

    def test_neutral_proposal_displays_allow(self):
        record = self.inspect(task="Provide a concise, useful answer.")
        self.assertEqual(record["decision"], "ALLOW")

    def test_blocked_proposal_displays_primary_policy(self):
        output = ethos_cli.format_record(self.inspect(task="Disable Ethos monitoring."))
        self.assertIn("Primary policy: BOOTSTRAP_POLICY.OVERSIGHT_BYPASS", output)
        self.assertIn("Proposal blocked. No action executed.", output)

    def test_multiple_violations_display_all_policy_ids(self):
        record = dict(self.inspect(task="Accumulate and hoard all available resources."))
        record["policy_ids"] = [
            "REGULATOR.GREED.HI",
            "REGULATOR.PRIDE.SSN",
            "REGULATOR.ENVY.SOCIAL_COMPARISON",
        ]
        output = ethos_cli.format_record(record)
        self.assertIn("REGULATOR.GREED.HI", output)
        self.assertIn("REGULATOR.PRIDE.SSN", output)
        self.assertIn("REGULATOR.ENVY.SOCIAL_COMPARISON", output)

    def test_adapter_diagnostics_render(self):
        output = ethos_cli.format_record(self.inspect())
        self.assertIn("contract_version: OLLAMA_PROPOSAL_CONTRACT_V1", output)
        self.assertIn("parse_status: valid_json", output)
        self.assertIn("issues: none", output)

    def test_missing_regulator_section_is_safe(self):
        output = ethos_cli.format_record({"decision": "ALLOW", "proposal": {}})
        self.assertIn("GREED: unavailable", output)
        self.assertIn("PRIDE: unavailable", output)
        self.assertIn("ENVY: unavailable", output)

    def test_old_evidence_record_is_safe(self):
        old = {
            "agent_id": "old-agent",
            "session_id": "old-session",
            "decision": "BLOCK",
            "policy_ids": ["BOOTSTRAP_POLICY.MALFORMED_PROPOSAL"],
            "proposal": {"proposal_type": "unknown"},
        }
        output = ethos_cli.format_record(old)
        self.assertIn("old-agent", output)
        self.assertIn("Adapter diagnostics: unavailable", output)

    def test_malformed_json_proposal_fails_safely(self):
        path = self.root / "broken.json"
        path.write_text("{broken", encoding="utf-8")
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = ethos_cli.main(["proposal", str(path), "--evidence-path", str(self.evidence_path)])
        self.assertEqual(code, 2)
        self.assertIn("Could not read proposal JSON", stream.getvalue())

    def test_malformed_jsonl_line_does_not_crash_viewer(self):
        self.evidence_path.write_text('{"decision":"ALLOW"}\nnot json\n\n', encoding="utf-8")
        records, skipped = ethos_cli.read_evidence(self.evidence_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(skipped, 1)

    def test_json_mode_emits_valid_structured_record(self):
        proposal_path = self.saved_path()
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = ethos_cli.main(
                ["proposal", str(proposal_path), "--evidence-path", str(self.evidence_path), "--json"]
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stream.getvalue())["decision"], "ALLOW")

    def test_live_ollama_path_can_be_mocked(self):
        proposal = ActionProposal.from_mapping(self.proposal())
        with patch("ethos_cli.OllamaProposalAdapter") as adapter_type:
            adapter_type.return_value.propose.return_value = proposal
            record = ethos_cli.inspect_ollama_task(
                "ignored in mock", "unit-test-model", self.evidence_path, "agent", "session"
            )
        self.assertEqual(record["decision"], "ALLOW")
        self.assertEqual(adapter_type.return_value.propose.call_count, 1)

    def test_explicit_structured_saved_input_passes_through_without_text_reconciliation(self):
        structured = self.proposal(
            task="operate on object B; proposal_id=fake-id; target_type=SERVICE; retaliation aggression",
            target="object B",
            raw_model_output="executed verified authorized; target_id=fake-target",
            proposal_id="caller-proposal-9",
            declared_targets=[{"target_id": "participant-a", "target_type": "PARTICIPANT"}],
        )
        path = self.root / "structured.json"
        path.write_text(json.dumps(structured), encoding="utf-8")
        proposal = ethos_cli.load_saved_proposal_for_inspection(path)
        self.assertIsInstance(proposal, ActionProposal)
        self.assertEqual(proposal.proposal_id, "caller-proposal-9")
        self.assertEqual(proposal.declared_targets[0].target_id, "participant-a")
        self.assertEqual(proposal.declared_targets[0].target_type, "PARTICIPANT")
        self.assertEqual(proposal.target, "object B")
        self.assertEqual(proposal.raw_model_output, structured["raw_model_output"])
        record = ethos_cli.inspect_saved_proposal(path, self.evidence_path)
        self.assertEqual(record["proposal"]["proposal_id"], "caller-proposal-9")
        self.assertEqual(record["proposal"]["declared_targets"], structured["declared_targets"])

    def test_legacy_saved_input_uses_existing_mapping_path_and_same_evidence_shape(self):
        path = self.saved_path()
        proposal = ethos_cli.load_saved_proposal_for_inspection(path)
        self.assertIsInstance(proposal, dict)
        record = ethos_cli.inspect_saved_proposal(path, self.evidence_path)
        self.assertNotIn("proposal_id", record["proposal"])
        self.assertNotIn("declared_targets", record["proposal"])

    def test_invalid_explicit_structured_saved_input_is_rejected_before_gate(self):
        invalid_cases = [
            {"proposal_id": ""},
            {"declared_targets": [{"target_type": "OBJECT"}]},
            {"declared_targets": [{"target_id": "x"}]},
            {"declared_targets": [{"target_id": "x", "target_type": "object"}]},
            {"declared_targets": [{"target_id": "x", "target_type": "OBJECT"}, {"target_id": "x", "target_type": "OBJECT"}]},
            {"declared_targets": [{"target_id": "x", "target_type": "OBJECT"}, {"target_id": "x", "target_type": "PARTICIPANT"}]},
        ]
        for index, change in enumerate(invalid_cases):
            with self.subTest(change=change):
                path = self.root / f"invalid-{index}.json"
                path.write_text(json.dumps(self.proposal(**change)), encoding="utf-8")
                with self.assertRaises(ethos_cli.CliError):
                    ethos_cli.inspect_saved_proposal(path, self.evidence_path)

    def test_structured_metadata_is_gate_and_regulator_neutral(self):
        legacy = self.inspect(task="Provide a concise, useful answer.")
        structured = self.inspect(
            task="Provide a concise, useful answer.", proposal_id="neutral-9",
            declared_targets=[{"target_id": "self", "target_type": "PARTICIPANT"}],
        )
        self.assertEqual(structured["decision"], legacy["decision"])
        self.assertEqual(structured["policy_ids"], legacy["policy_ids"])
        self.assertEqual(structured["regulators"], legacy["regulators"])

    def test_structured_cli_input_round_trips_to_test_only_v11_evidence(self):
        path = self.saved_path(
            proposal_id="round-trip-9",
            declared_targets=[
                {"target_id": "cli-test-01", "target_type": "PARTICIPANT"},
                {"target_id": "file-9", "target_type": "OBJECT"},
                {"target_id": "task-9", "target_type": "TASK"},
            ],
        )
        proposal = ethos_cli.load_saved_proposal_for_inspection(path)
        self.assertIsInstance(proposal, ActionProposal)
        packet = produce_declared_envelope(proposal, "cli-fixture-9")
        text = canonical_json(packet)
        self.assertEqual(validate_packet(packet).disposition, Disposition.STRUCTURAL)
        self.assertEqual(text, canonical_json(produce_declared_envelope(proposal, "cli-fixture-9")))
        self.assertEqual(text, canonical_json(from_canonical_json(text)))
        self.assertEqual(packet.entities[1].entity_id, "round-trip-9")
        self.assertEqual([relation.endpoints[1].entity_id for relation in packet.relations], ["cli-test-01", "file-9", "task-9"])

    def test_cli_path_preserves_zero_one_and_scoped_multiple_targets(self):
        zero = ethos_cli.load_saved_proposal_for_inspection(self.saved_path(proposal_id="zero-9", declared_targets=[]))
        one = ethos_cli.load_saved_proposal_for_inspection(self.saved_path(proposal_id="one-9", declared_targets=[{"target_id": "self", "target_type": "PARTICIPANT"}]))
        first = self.root / "first.json"
        second = self.root / "second.json"
        first.write_text(json.dumps(self.proposal(agent_id="agent-one", session_id="session-one", proposal_id="many-1", declared_targets=[{"target_id": "1", "target_type": "OBJECT"}, {"target_id": "self", "target_type": "PARTICIPANT"}])), encoding="utf-8")
        second.write_text(json.dumps(self.proposal(agent_id="agent-two", session_id="session-two", proposal_id="many-2", declared_targets=[{"target_id": "1", "target_type": "OBJECT"}])), encoding="utf-8")
        self.assertEqual(zero.declared_targets, ())
        self.assertEqual(len(one.declared_targets), 1)
        first_proposal = ethos_cli.load_saved_proposal_for_inspection(first)
        second_proposal = ethos_cli.load_saved_proposal_for_inspection(second)
        self.assertEqual(len(first_proposal.declared_targets), 2)
        self.assertEqual(first_proposal.declared_targets[0].target_id, second_proposal.declared_targets[0].target_id)
        self.assertNotEqual(first_proposal.session_id, second_proposal.session_id)
        self.assertEqual(produce_declared_envelope(zero, "zero-fixture-9").relations, ())
        self.assertEqual(produce_declared_envelope(one, "one-fixture-9").relations[0].endpoints[1].entity_id, "self")
        self.assertEqual(validate_packet(produce_declared_envelope(first_proposal, "many-fixture-9")).disposition, Disposition.STRUCTURAL)

    def test_no_execution_path_exists(self):
        source = Path(ethos_cli.__file__).read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "exec(", "eval("):
            self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(ethos_cli, "execute"))


if __name__ == "__main__":
    unittest.main()

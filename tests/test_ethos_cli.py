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

    def test_no_execution_path_exists(self):
        source = Path(ethos_cli.__file__).read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "exec(", "eval("):
            self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(ethos_cli, "execute"))


if __name__ == "__main__":
    unittest.main()

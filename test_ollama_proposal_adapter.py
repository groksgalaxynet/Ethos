"""Deterministic contract tests for the fail-closed Ollama proposal adapter."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore
from greed_analyzer import GREED_DIMENSIONS, GreedAnalyzer, GreedConfig
from ollama_proposal_adapter import MODEL_PROPOSAL_TYPES, OllamaAdapterError, OllamaProposalAdapter


class OllamaProposalAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = OllamaProposalAdapter(model="unit-test-model")

    def payload(self, proposal_type="respond", **overrides):
        value = {
            "proposal_type": proposal_type,
            "target": "chat",
            "arguments": {"text": "hello"},
            "exposed_reasoning": "A concise response meets the task.",
        }
        value.update(overrides)
        return value

    def normalize(self, raw):
        return self.adapter._proposal_from_output(raw, "test task", "agent-1", "session-1")

    def test_valid_json_parses(self):
        proposal = self.normalize(json.dumps(self.payload()))
        self.assertEqual(proposal.proposal_type, "respond")
        self.assertEqual(proposal.adapter_diagnostics["parse_status"], "valid_json")
        self.assertEqual(proposal.adapter_diagnostics["validation_status"], "valid")

    def test_fenced_json_parses(self):
        proposal = self.normalize("```json\n" + json.dumps(self.payload()) + "\n```")
        self.assertEqual(proposal.proposal_type, "respond")
        self.assertEqual(proposal.adapter_diagnostics["parse_status"], "fenced_json")
        self.assertEqual(proposal.adapter_diagnostics["repair_applied"], "strip_markdown_fence")

    def test_whitespace_parses(self):
        proposal = self.normalize(" \n\t" + json.dumps(self.payload()) + " \n")
        self.assertEqual(proposal.proposal_type, "respond")

    def test_unambiguous_surrounding_prose_is_recovered(self):
        proposal = self.normalize("Here is the proposal: " + json.dumps(self.payload()) + " End.")
        self.assertEqual(proposal.proposal_type, "respond")
        self.assertEqual(proposal.adapter_diagnostics["parse_status"], "extracted_json")

    def test_malformed_json_fails_closed(self):
        proposal = self.normalize('{"proposal_type": "respond"')
        self.assertEqual(proposal.proposal_type, "unknown")
        self.assertIn("invalid_json", proposal.adapter_diagnostics["issues"])

    def test_missing_proposal_type_fails_closed(self):
        payload = self.payload()
        del payload["proposal_type"]
        proposal = self.normalize(json.dumps(payload))
        self.assertEqual(proposal.proposal_type, "unknown")
        self.assertIn("invalid_proposal_type", proposal.adapter_diagnostics["issues"])

    def test_invalid_proposal_type_fails_closed(self):
        proposal = self.normalize(json.dumps(self.payload(proposal_type="teleport")))
        self.assertEqual(proposal.proposal_type, "unknown")
        self.assertIn("invalid_proposal_type", proposal.adapter_diagnostics["issues"])

    def test_each_model_proposal_type_is_accepted(self):
        for proposal_type in MODEL_PROPOSAL_TYPES:
            with self.subTest(proposal_type=proposal_type):
                proposal = self.normalize(json.dumps(self.payload(proposal_type=proposal_type)))
                self.assertEqual(proposal.proposal_type, proposal_type)

    def test_invalid_arguments_fail_closed(self):
        proposal = self.normalize(json.dumps(self.payload(arguments=["not", "an", "object"])))
        self.assertEqual(proposal.proposal_type, "unknown")
        self.assertIn("invalid_arguments", proposal.adapter_diagnostics["issues"])

    def test_unexpected_fields_fail_closed(self):
        proposal = self.normalize(json.dumps(self.payload(extra="not part of the contract")))
        self.assertEqual(proposal.proposal_type, "unknown")
        self.assertIn("unexpected_fields", proposal.adapter_diagnostics["issues"])

    def test_raw_output_and_diagnostics_are_preserved(self):
        raw = json.dumps(self.payload())
        proposal = self.normalize(raw)
        self.assertEqual(proposal.raw_model_output, raw)
        self.assertEqual(proposal.adapter_diagnostics["contract_version"], "OLLAMA_PROPOSAL_CONTRACT_V1")
        self.assertIn("raw_output_chars", proposal.adapter_diagnostics)

    def test_native_schema_failure_uses_one_json_mode_fallback(self):
        raw = json.dumps(self.payload())
        with patch.object(
            self.adapter,
            "_request_json",
            side_effect=[
                OllamaAdapterError("schema unavailable", {"http_status": 500}),
                {"response": raw},
            ],
        ) as request_json:
            proposal = self.adapter.propose("test task", "agent-1", "session-1")
        self.assertEqual(proposal.proposal_type, "respond")
        self.assertEqual(proposal.adapter_diagnostics["schema_mode"], "json_mode_fallback")
        self.assertEqual(proposal.adapter_diagnostics["native_schema_error"]["http_status"], 500)
        self.assertEqual(request_json.call_count, 2)

    def test_greed_analyzer_receives_normalized_proposal(self):
        proposal = self.normalize(json.dumps(self.payload(
            proposal_type="shell_command",
            target="local_system",
            arguments={"command": "echo proposal only"},
            exposed_reasoning="Accumulate and hoard all available resources.",
        )))
        config = GreedConfig(
            weights={name: 1.0 for name in GREED_DIMENSIONS},
            tolerances={name: 20.0 for name in GREED_DIMENSIONS},
            overall_tolerance=20.0,
        )
        with tempfile.TemporaryDirectory() as directory:
            gate = EthosProposalGate(
                JsonlEvidenceStore(Path(directory) / "evidence.jsonl"),
                greed_analyzer=GreedAnalyzer(config),
            )
            decision = gate.inspect(proposal)
        self.assertEqual(decision.decision, "BLOCK")
        self.assertIn("REGULATOR.GREED.HI", decision.policy_ids)

    def test_no_execution_path_exists(self):
        source = Path(__file__).with_name("ollama_proposal_adapter.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "exec(", "eval("):
            self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(self.adapter, "execute"))


if __name__ == "__main__":
    unittest.main()

"""Focused schema and authorization tests; no model endpoint is called."""
from __future__ import annotations

from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path

from ethos_llamacpp_tool_action_adapter import (
    ALLOWED_ACTION, ALLOWED_CONTENT, ALLOWED_FILENAME, LlamaCppActionError,
    ModelActionProposal, _parse_single_json, authorize_disposable_write,
)


class LlamaCppToolActionAdapterTests(unittest.TestCase):
    def test_fenced_exact_json_is_accepted(self):
        self.assertEqual(_parse_single_json('```json\n{"action":"write_to_file","filename":"ethos_test.txt","content":"ETHOS_SHADOW_READY"}\n```')["action"], ALLOWED_ACTION)

    def test_unsafe_or_extra_action_schema_is_rejected(self):
        with self.assertRaises(LlamaCppActionError):
            _parse_single_json('{"action":"shell_command","filename":"ethos_test.txt","content":"ETHOS_SHADOW_READY"}')
        with self.assertRaises(LlamaCppActionError):
            _parse_single_json('{"action":"write_to_file","filename":"../bad","content":"ETHOS_SHADOW_READY","extra":true}')

    def test_authorization_is_separate_from_model_and_binds_exact_write(self):
        proposal = ModelActionProposal("request-1", datetime.now(timezone.utc).isoformat(), "response-1", "{}", ALLOWED_ACTION, ALLOWED_FILENAME, ALLOWED_CONTENT)
        with tempfile.TemporaryDirectory() as directory:
            request = authorize_disposable_write(proposal=proposal, disposable_root=directory, authorization_reference="USER_PHASE5E_AUTHORIZATION")
            self.assertEqual(request.action_type, "WRITE_TEXT")
            self.assertEqual(request.provenance, "REAL_RUNTIME")
            self.assertEqual(request.authorization_reference, "USER_PHASE5E_AUTHORIZATION")


if __name__ == "__main__":
    unittest.main()

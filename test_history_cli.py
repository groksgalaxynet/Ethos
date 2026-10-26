"""Focused Task 9 tests for the read-only violation-history CLI view."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import ethos_cli
from scar_service import ScarService
from violation_history import ConsequenceService, ViolationHistory, utc_now


class HistoryCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db_path = self.root / "evidence.violations.db"
        self.evidence_path = self.root / "evidence.jsonl"
        self.scar_root = self.root / "evidence_scar_runtime"
        self.history = ViolationHistory(self.db_path)
        self.service = ConsequenceService(self.history, ScarService(self.scar_root))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def block(
        self,
        number: int,
        *,
        agent_id: str = "history-agent",
        session_id: str = "history-session",
        policy_id: str = "REGULATOR.GREED.HI",
    ) -> dict:
        return self.service.apply_block(
            evidence_id=f"history-evidence-{number}",
            agent_id=agent_id,
            session_id=session_id,
            timestamp=utc_now(),
            proposal_type="respond",
            primary_policy_id=policy_id,
            policy_ids=(policy_id,),
            decision="BLOCK",
            evidence_path=str(self.evidence_path),
        )

    def cli(self, *arguments: str) -> tuple[int, str]:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = ethos_cli.main(["history", str(self.db_path), *arguments])
        return code, stream.getvalue()

    def test_empty_valid_history_renders_safely(self):
        code, output = self.cli()
        self.assertEqual(code, 0)
        self.assertIn("Total stored violations: 0", output)
        self.assertIn("No matching violation records found.", output)

    def test_one_violation_renders_required_fields(self):
        self.block(1)
        code, output = self.cli()
        self.assertEqual(code, 0)
        self.assertIn("Agent ID: history-agent", output)
        self.assertIn("Primary policy ID: REGULATOR.GREED.HI", output)
        self.assertIn("Policy family: REGULATOR.GREED", output)
        self.assertIn("Repeat count: 1", output)
        self.assertIn("Consequence state: WARNING", output)

    def test_repeated_violation_shows_repeat_count(self):
        self.block(1)
        self.block(2)
        _, output = self.cli("--recent", "1")
        self.assertIn("Repeat count: 2", output)
        self.assertIn("Consequence state: MINOR_SCAR", output)

    def test_history_shows_repeated_and_bounded_consequence_states(self):
        for number in range(1, 6):
            self.block(number)
        _, output = self.cli("--recent", "3")
        self.assertIn("Consequence state: MAJOR_SCAR", output)
        self.assertIn("Consequence state: REPEATED_AFTER_MINOR", output)

    def test_greed_vectors_visibly_share_regulator_family(self):
        self.block(1, policy_id="REGULATOR.GREED.HI")
        self.block(2, policy_id="REGULATOR.GREED.RHI")
        _, output = self.cli("--recent", "2")
        self.assertIn("Primary policy ID: REGULATOR.GREED.RHI", output)
        self.assertEqual(output.count("Policy family: REGULATOR.GREED"), 2)

    def test_minor_scar_linkage_renders_existing_ledger_metadata(self):
        self.block(1)
        self.block(2)
        _, output = self.cli("--recent", "1")
        self.assertIn("Scar severity: Minor", output)
        self.assertIn("Scar metadata:", output)
        self.assertIn("Reason: Ethos repeated blocked policy", output)

    def test_major_scar_linkage_renders_existing_ledger_metadata(self):
        for number in range(1, 5):
            self.block(number)
        _, output = self.cli("--recent", "1")
        self.assertIn("Scar severity: Major", output)
        self.assertIn("Scar metadata:", output)

    def test_no_scar_record_renders_safely(self):
        self.block(1)
        _, output = self.cli()
        self.assertIn("Scar created: no", output)
        self.assertIn("Scar ID: none", output)

    def test_missing_scar_ledger_does_not_crash(self):
        self.block(1)
        self.history.update_consequence(
            "history-evidence-1",
            scar_created=False,
            scar_id=999,
            scar_severity="Minor",
            scar_reason="test-only missing ledger linkage",
            status="recorded_existing_scar",
        )
        code, output = self.cli()
        self.assertEqual(code, 0)
        self.assertIn("Scar metadata unavailable", output)

    def test_missing_scar_file_does_not_crash_metadata_view(self):
        self.block(1)
        consequence = self.block(2)
        scar = ScarService(self.scar_root).get_scar(consequence["scar_id"])
        self.assertIsNotNone(scar)
        (self.scar_root / "scars" / scar.file).unlink()
        code, output = self.cli("--recent", "1")
        self.assertEqual(code, 0)
        self.assertIn("Scar metadata:", output)

    def test_recent_limits_returned_records(self):
        self.block(1)
        self.block(2)
        _, output = self.cli("--recent", "1")
        self.assertIn("Violation ID: 2", output)
        self.assertNotIn("Violation ID: 1", output)

    def test_agent_filter_works(self):
        self.block(1, agent_id="agent-a")
        self.block(2, agent_id="agent-b")
        _, output = self.cli("--agent-id", "agent-a")
        self.assertIn("Agent ID: agent-a", output)
        self.assertNotIn("Agent ID: agent-b", output)

    def test_policy_family_filter_works(self):
        self.block(1, policy_id="REGULATOR.GREED.HI")
        self.block(2, policy_id="BOOTSTRAP_POLICY.OVERSIGHT_BYPASS")
        _, output = self.cli("--policy-family", "BOOTSTRAP_POLICY.OVERSIGHT_BYPASS")
        self.assertIn("Policy family: BOOTSTRAP_POLICY.OVERSIGHT_BYPASS", output)
        self.assertNotIn("Policy family: REGULATOR.GREED", output)

    def test_json_history_output_is_structured_and_includes_scar_metadata(self):
        self.block(1)
        self.block(2)
        code, output = self.cli("--json")
        view = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(view["summary"]["total_stored_violations"], 2)
        self.assertEqual(view["violations"][0]["policy_family"], "REGULATOR.GREED")
        self.assertEqual(view["violations"][0]["consequence_state"], "MINOR_SCAR")
        self.assertIsInstance(view["violations"][0]["scar_metadata"], dict)

    def test_unsupported_schema_fails_safely(self):
        unsupported = self.root / "unsupported.db"
        with sqlite3.connect(unsupported) as connection:
            connection.execute("CREATE TABLE unrelated(value TEXT)")
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = ethos_cli.main(["history", str(unsupported)])
        self.assertEqual(code, 2)
        self.assertIn("Unsupported violation-history schema", stream.getvalue())

    def test_history_view_does_not_mutate_database_or_scar_files(self):
        self.block(1)
        self.block(2)
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        code, _ = self.cli("--json")
        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(code, 0)
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()

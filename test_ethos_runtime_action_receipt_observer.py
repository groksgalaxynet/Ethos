"""Focused receipt-to-shadow tests; they use a disposable synthetic target."""
from __future__ import annotations

from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path

from ethos_generic_shadow_config import configured_shadow
from ethos_generic_shadow_observation import ShadowPaths, load_observations
from ethos_local_tool_execution_receipts import IsolatedLocalToolBoundary, ToolActionRequest, load_receipts
from ethos_runtime_action_receipt_observer import observe_receipt


class ReceiptObserverTests(unittest.TestCase):
    def test_actual_disposable_write_yields_receipt_and_incomplete_shadow_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            boundary = IsolatedLocalToolBoundary(disposable_root=root / "target", receipt_path=root / "receipts.jsonl")
            request = ToolActionRequest(
                "fixture-request", datetime.now(timezone.utc).isoformat(), "fixture-local-ai",
                "SYNTHETIC_FIXTURE", "fixture-authorization", "WRITE_TEXT", "harmless.txt",
                "harmless fixture output", "SYNTHETIC_FIXTURE",
            )
            receipt = boundary.execute(request)
            self.assertEqual(receipt.status, "EXECUTED")
            self.assertEqual((root / "target" / "harmless.txt").read_text(encoding="utf-8"), "harmless fixture output")
            self.assertEqual(load_receipts(root / "receipts.jsonl")[1], ())
            configurations = {name: configured_shadow(name, enabled=name == "wrath", storage_root=root / "shadow") for name in ("wrath", "gluttony", "lust")}
            outcomes = observe_receipt(receipt=receipt, configurations=configurations)
            wrath = outcomes[0]
            self.assertTrue(wrath.classifier_invoked)
            self.assertTrue(wrath.observation_persisted)
            self.assertEqual(wrath.enforcement, "NONE")
            self.assertEqual(wrath.activation, "ACTIVE")
            observations, issues = load_observations(ShadowPaths("wrath", root / "shadow"))
            self.assertEqual(issues, ())
            self.assertEqual(observations[0].provenance, "SYNTHETIC_FIXTURE")
            self.assertEqual(observations[0].classification.state, "INSUFFICIENT_EVIDENCE")

    def test_unsafe_target_is_refused_and_receipt_is_still_observable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            boundary = IsolatedLocalToolBoundary(disposable_root=root / "target", receipt_path=root / "receipts.jsonl")
            request = ToolActionRequest("fixture-refusal", datetime.now(timezone.utc).isoformat(), "fixture-agent", "SYNTHETIC_FIXTURE", "fixture-auth", "WRITE_TEXT", "../outside.txt", "no write", "SYNTHETIC_FIXTURE")
            receipt = boundary.execute(request)
            self.assertEqual(receipt.status, "REFUSED")
            self.assertEqual(receipt.outcome_reference, "REFUSED_OUTSIDE_DISPOSABLE_ROOT")


if __name__ == "__main__":
    unittest.main()

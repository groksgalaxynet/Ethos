"""Focused tests for the read-only adaptation of legacy drift hash observation."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from artifact_observer import ArtifactSpec, observe_artifact, observe_artifacts


class ArtifactObserverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def snapshot(self) -> dict[Path, bytes]:
        return {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}

    def test_raw_artifact_is_unchanged_then_detects_modified_copy(self) -> None:
        artifact = self.root / "policy.json"
        artifact.write_text('{"policy":"fixed"}', encoding="utf-8")
        first = observe_artifact(ArtifactSpec("policy", artifact))
        self.assertEqual(first.status, "UNTRACKED")
        stable = observe_artifact(ArtifactSpec("policy", artifact, expected_hash=first.observed_hash))
        self.assertEqual(stable.status, "UNCHANGED")
        artifact.write_text('{"policy":"changed"}', encoding="utf-8")
        self.assertEqual(observe_artifact(ArtifactSpec("policy", artifact, expected_hash=first.observed_hash)).status, "CHANGED")

    def test_missing_artifact_is_unavailable_without_creation(self) -> None:
        missing = self.root / "missing.json"
        result = observe_artifact(ArtifactSpec("missing", missing))
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertFalse(missing.exists())

    def test_canonical_evidence_packet_ignores_json_key_order(self) -> None:
        first_path, second_path = self.root / "first.json", self.root / "second.json"
        first_path.write_text(json.dumps({"event": {"decision": "BLOCK", "evidence_id": "one"}, "schema_version": "x"}), encoding="utf-8")
        second_path.write_text(json.dumps({"schema_version": "x", "event": {"evidence_id": "one", "decision": "BLOCK"}}), encoding="utf-8")
        expected = observe_artifact(ArtifactSpec("first", first_path, "evidence-packet")).observed_hash
        result = observe_artifact(ArtifactSpec("second", second_path, "evidence-packet", expected))
        self.assertEqual(result.status, "UNCHANGED")

    def test_observation_is_read_only_deterministic_and_independent(self) -> None:
        first, second = self.root / "first.txt", self.root / "second.txt"
        first.write_text("same", encoding="utf-8")
        second.write_text("other", encoding="utf-8")
        before = self.snapshot()
        baseline = observe_artifact(ArtifactSpec("first", first))
        observations = observe_artifacts([
            ArtifactSpec("second", second, expected_hash="not-the-real-hash"),
            ArtifactSpec("first", first, expected_hash=baseline.observed_hash),
        ])
        self.assertEqual([item.identity for item in observations], ["first", "second"])
        self.assertEqual([item.status for item in observations], ["UNCHANGED", "CHANGED"])
        self.assertEqual(observe_artifact(ArtifactSpec("first", first, expected_hash=baseline.observed_hash)), observations[0])
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()

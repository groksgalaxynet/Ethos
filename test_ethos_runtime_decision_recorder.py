import json
from pathlib import Path
import tempfile
import unittest

from ethos_runtime_decision_recorder import (
    DEFAULT_DECISION_LOG_PATH,
    SCHEMA_VERSION,
    RuntimeActionCandidate,
    RuntimeDecisionRecord,
    RuntimeDecisionRecorder,
    load_decision_log,
    to_research_entry,
    validate,
)


def candidates(source="planner"):
    return (
        RuntimeActionCandidate("action-a", "tool", source),
        RuntimeActionCandidate("action-b", "tool", source),
    )


def record(sequence=1, timestamp="2026-10-02T01:00:00Z", **changes):
    values = dict(
        schema_version=SCHEMA_VERSION, decision_id="decision-1", sequence_id=sequence,
        timestamp=timestamp, source_instance_id="instance", actor_id="agent",
        objective_id="objective", scope_id="scope", candidates=candidates(),
        selected_action_id="action-b", candidate_source="planner", recorder_source="recorder",
    )
    values.update(changes)
    return RuntimeDecisionRecord(**values)


class RuntimeDecisionRecorderTests(unittest.TestCase):
    def test_default_location_is_dedicated_jsonl_file(self):
        self.assertEqual(DEFAULT_DECISION_LOG_PATH.name, "runtime_decisions.jsonl")
        self.assertEqual(DEFAULT_DECISION_LOG_PATH.parent.name, "evidence")

    def test_record_reload_order_and_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.jsonl"
            recorder = RuntimeDecisionRecorder(path, source_instance_id="instance")
            first = recorder.record_decision(
                actor_id="agent", objective_id="objective", scope_id="scope",
                candidates=candidates(), selected_action_id="action-b", candidate_source="planner",
                decision_id="decision-1", timestamp="2026-10-02T01:00:00Z",
            )
            recorder.record_decision(
                actor_id="agent", objective_id="objective", scope_id="scope",
                candidates=candidates("controller"), selected_action_id="action-a",
                candidate_source="controller", decision_id="decision-2",
                timestamp="2026-10-02T02:00:00Z",
            )
            report = load_decision_log(path)
            self.assertEqual(report.issues, ())
            self.assertEqual([item.sequence_id for item in report.records], [1, 2])
            self.assertEqual([item.selected_action_id for item in report.records], ["action-b", "action-a"])
            adapted = to_research_entry(first)
            self.assertEqual(adapted.decision.record_id, "decision-1")
            self.assertEqual(adapted.decision.selected_action_id, "action-b")
            self.assertEqual(adapted.sequence_id, 1)
            self.assertEqual(adapted.decision.candidates[0].available, "UNKNOWN")
            self.assertEqual(adapted.decision.candidates[0].required_status, "UNKNOWN")

    def test_validation_accepts_complete_neutral_record(self):
        self.assertEqual(validate(record()), ())

    def test_validation_rejects_unknown_selected_action(self):
        self.assertIn("SELECTED_ACTION_NOT_CANDIDATE", validate(record(selected_action_id="missing")))

    def test_validation_rejects_duplicate_candidate_ids(self):
        duplicate = (RuntimeActionCandidate("a", "tool", "planner"),) * 2
        self.assertIn("DUPLICATE_CANDIDATE_ID", validate(record(candidates=duplicate, selected_action_id="a")))

    def test_validation_rejects_empty_candidates(self):
        self.assertIn("EMPTY_CANDIDATES", validate(record(candidates=())))

    def test_validation_rejects_malformed_candidate(self):
        bad = (RuntimeActionCandidate("", "tool", "planner"),)
        self.assertIn("MALFORMED_CANDIDATE", validate(record(candidates=bad)))

    def test_validation_rejects_unsupported_schema(self):
        self.assertIn("UNSUPPORTED_SCHEMA", validate(record(schema_version="V9")))

    def test_validation_rejects_missing_identity_and_source(self):
        self.assertIn("MISSING_IDENTITY_OR_SOURCE", validate(record(actor_id="")))

    def test_validation_requires_decision_id(self):
        self.assertIn("MISSING_IDENTITY_OR_SOURCE", validate(record(decision_id="")))

    def test_validation_requires_timestamp(self):
        self.assertIn("MISSING_IDENTITY_OR_SOURCE", validate(record(timestamp="")))

    def test_validation_requires_source_instance(self):
        self.assertIn("MISSING_IDENTITY_OR_SOURCE", validate(record(source_instance_id="")))

    def test_validation_requires_objective(self):
        self.assertIn("MISSING_IDENTITY_OR_SOURCE", validate(record(objective_id="")))

    def test_validation_requires_scope(self):
        self.assertIn("MISSING_IDENTITY_OR_SOURCE", validate(record(scope_id="")))

    def test_validation_requires_candidate_set_source(self):
        self.assertIn("MISSING_IDENTITY_OR_SOURCE", validate(record(candidate_source="")))

    def test_validation_requires_recorder_source(self):
        self.assertIn("MISSING_IDENTITY_OR_SOURCE", validate(record(recorder_source="")))

    def test_validation_rejects_invalid_sequence(self):
        self.assertIn("INVALID_SEQUENCE", validate(record(sequence=0)))

    def test_validation_rejects_invalid_timestamp(self):
        self.assertIn("INVALID_TIMESTAMP", validate(record(timestamp="not-a-time")))

    def test_validation_rejects_candidate_without_kind(self):
        bad = (RuntimeActionCandidate("action-a", "", "planner"),)
        self.assertIn("MALFORMED_CANDIDATE", validate(record(candidates=bad, selected_action_id="action-a")))

    def test_validation_rejects_candidate_without_source(self):
        bad = (RuntimeActionCandidate("action-a", "tool", ""),)
        self.assertIn("MALFORMED_CANDIDATE", validate(record(candidates=bad, selected_action_id="action-a")))

    def test_invalid_write_does_not_consume_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = RuntimeDecisionRecorder(Path(directory) / "log", source_instance_id="one")
            with self.assertRaises(ValueError):
                recorder.record_decision(
                    actor_id="agent", objective_id="objective", scope_id="scope", candidates=(),
                    selected_action_id="action-a", candidate_source="planner",
                )
            written = recorder.record_decision(
                actor_id="agent", objective_id="objective", scope_id="scope", candidates=candidates(),
                selected_action_id="action-a", candidate_source="planner",
            )
            self.assertEqual(written.sequence_id, 1)

    def test_loader_flags_malformed_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            path.write_text("{broken\n", encoding="utf-8")
            self.assertEqual(load_decision_log(path).issues, ("MALFORMED_ENTRY:1",))

    def test_loader_flags_duplicate_decision_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            entries = (record(sequence=1, decision_id="same"), record(sequence=2, decision_id="same", timestamp="2026-10-02T02:00:00Z"))
            path.write_text("\n".join(json.dumps(item.to_dict()) for item in entries), encoding="utf-8")
            self.assertIn("DUPLICATE_DECISION_ID", load_decision_log(path).issues)

    def test_loader_flags_duplicate_sequence_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            entries = (record(decision_id="one"), record(decision_id="two", timestamp="2026-10-02T02:00:00Z"))
            path.write_text("\n".join(json.dumps(item.to_dict()) for item in entries), encoding="utf-8")
            report = load_decision_log(path)
            self.assertIn("DUPLICATE_SEQUENCE_ID:instance", report.issues)
            self.assertIn("INVALID_SEQUENCE_ORDER:instance", report.issues)

    def test_loader_flags_reversed_sequence_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            later = record(sequence=2, decision_id="two", timestamp="2026-10-02T02:00:00Z")
            earlier = record(sequence=1, decision_id="one", timestamp="2026-10-02T01:00:00Z")
            path.write_text("\n".join(json.dumps(item.to_dict()) for item in (later, earlier)), encoding="utf-8")
            self.assertIn("INVALID_SEQUENCE_ORDER:instance", load_decision_log(path).issues)

    def test_loader_flags_reversed_chronology(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            entries = (
                record(decision_id="one", timestamp="2026-10-02T02:00:00Z"),
                record(sequence=2, decision_id="two", timestamp="2026-10-02T01:00:00Z"),
            )
            path.write_text("\n".join(json.dumps(item.to_dict()) for item in entries), encoding="utf-8")
            self.assertIn("INVALID_CHRONOLOGY:instance", load_decision_log(path).issues)

    def test_loader_flags_noncontiguous_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            entries = (record(decision_id="one"), record(sequence=3, decision_id="three", timestamp="2026-10-02T03:00:00Z"))
            path.write_text("\n".join(json.dumps(item.to_dict()) for item in entries), encoding="utf-8")
            self.assertIn("INVALID_SEQUENCE_ORDER:instance", load_decision_log(path).issues)

    def test_adapter_preserves_candidate_set_source(self):
        entry = to_research_entry(record(candidate_source="scheduler"))
        self.assertEqual(entry.decision.source.source_id, "scheduler")

    def test_adapter_preserves_source_instance_and_scope(self):
        entry = to_research_entry(record(source_instance_id="runtime-x", scope_id="job-x"))
        self.assertEqual((entry.source_instance_id, entry.scope_id), ("runtime-x", "job-x"))

    def test_adapter_does_not_invent_measurements(self):
        candidate = to_research_entry(record()).decision.candidates[0]
        self.assertEqual((candidate.benefit, candidate.effort, candidate.resource_cost), (None, None, None))

    def test_recording_does_not_create_execution_state(self):
        entry = to_research_entry(record())
        self.assertEqual(entry.execution_state, "UNKNOWN")

    def test_recorder_accepts_a_list_at_its_public_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = RuntimeDecisionRecorder(Path(directory) / "log", source_instance_id="list-input")
            written = recorder.record_decision(
                actor_id="agent", objective_id="objective", scope_id="scope", candidates=list(candidates()),
                selected_action_id="action-a", candidate_source="planner",
            )
            self.assertIsInstance(written.candidates, tuple)

    def test_candidate_level_source_is_retained_in_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            recorder = RuntimeDecisionRecorder(path, source_instance_id="candidate-source")
            recorder.record_decision(
                actor_id="agent", objective_id="objective", scope_id="scope",
                candidates=(RuntimeActionCandidate("action-a", "tool", "scheduler"),),
                selected_action_id="action-a", candidate_source="controller",
            )
            self.assertEqual(load_decision_log(path).records[0].candidates[0].candidate_source, "scheduler")

    def test_restart_uses_distinguishable_source_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            first = RuntimeDecisionRecorder(path, source_instance_id="before-restart")
            second = RuntimeDecisionRecorder(path, source_instance_id="after-restart")
            for recorder in (first, second):
                recorder.record_decision(
                    actor_id="agent", objective_id="objective", scope_id="scope", candidates=candidates(),
                    selected_action_id="action-a", candidate_source="planner", timestamp="2026-10-02T01:00:00Z",
                )
            report = load_decision_log(path)
            self.assertEqual(report.issues, ())
            self.assertEqual({item.source_instance_id for item in report.records}, {"before-restart", "after-restart"})
            self.assertEqual([item.sequence_id for item in report.records], [1, 1])

    def test_missing_log_returns_read_error(self):
        with tempfile.TemporaryDirectory() as directory:
            report = load_decision_log(Path(directory) / "missing")
            self.assertTrue(report.issues[0].startswith("READ_ERROR:"))

    def test_smoke_path_persists_and_reloads_neutral_test_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "smoke.jsonl"
            recorder = RuntimeDecisionRecorder(path, source_instance_id="smoke")
            written = recorder.record_decision(
                actor_id="runtime-smoke", objective_id="decision_recorder_smoke_test", scope_id="smoke",
                candidates=(
                    RuntimeActionCandidate("candidate-a", "test", "controller"),
                    RuntimeActionCandidate("candidate-b", "test", "controller"),
                ),
                selected_action_id="candidate-b", candidate_source="controller",
                timestamp="2026-10-02T01:00:00Z",
            )
            self.assertTrue(path.exists())
            self.assertEqual(load_decision_log(path).records, (written,))
            self.assertEqual(load_decision_log(path).issues, ())

import json
from pathlib import Path
import tempfile
import unittest

from ethos_runtime_assignment_producer import *
from ethos_runtime_decision_recorder import RuntimeActionCandidate, RuntimeDecisionRecorder


T1 = "2026-10-02T01:00:00Z"
T2 = "2026-10-02T02:00:00Z"
T3 = "2026-10-02T03:00:00Z"


def paths(directory):
    root = Path(directory)
    return root / "authority.jsonl", root / "assignments.jsonl", root / "lifecycle.jsonl"


def setup(directory, authority_type=ASSIGN_REQUIRED_WORK, valid_until=None, requirement="REQUIRED", actor="agent-1", scope="scope", issuer="controller"):
    authority, assignments, lifecycle = paths(directory)
    producer = RuntimeAssignmentProducer(authority, assignments, lifecycle, source_instance_id="producer")
    grant = producer.grant_authority(issuer_id="authority-root", authorized_principal_id=issuer, authority_type=authority_type, scope_id=scope, source_id="authority-root", source_type="SYSTEM_ASSERTION", valid_from=T1, valid_until=valid_until, grant_id="grant", timestamp=T1)
    assignment = producer.assign_work(objective_id="repair", work_id="inspect", assigned_actor_id=actor, issuer_id=issuer, scope_id=scope, requirement=requirement, authority_grant_id="grant", source_id=issuer, source_type="CONTROLLER", assignment_id="assignment", assignment_at=T2)
    return producer, grant, assignment, (authority, assignments, lifecycle)


def lifecycle_grant(producer, state, scope="scope", principal="controller"):
    authority_type = LIFECYCLE_AUTHORITY[state]
    return producer.grant_authority(issuer_id="authority-root", authorized_principal_id=principal, authority_type=authority_type, scope_id=scope, source_id="authority-root", source_type="SYSTEM_ASSERTION", valid_from=T1, grant_id=f"grant-{state}", timestamp=T1)


class RuntimeAssignmentProducerTests(unittest.TestCase):
    def test_valid_required_assignment_is_active(self):
        with tempfile.TemporaryDirectory() as directory:
            _, grants, assignment, _ = setup(directory)
            self.assertEqual(derive_assignment_state(assignment, (grants,), (), actor_id="agent-1", scope_id="scope", at=T3), "REQUIRED_ACTIVE")

    def test_valid_optional_assignment_is_optional_active(self):
        with tempfile.TemporaryDirectory() as directory:
            _, grant, assignment, _ = setup(directory, requirement="OPTIONAL")
            self.assertEqual(derive_assignment_state(assignment, (grant,), (), actor_id="agent-1", scope_id="scope", at=T3), "OPTIONAL_ACTIVE")

    def test_unknown_requirement_remains_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            _, grant, assignment, _ = setup(directory, requirement="UNKNOWN")
            self.assertEqual(derive_assignment_state(assignment, (grant,), (), actor_id="agent-1", scope_id="scope", at=T3), "UNKNOWN_REQUIREMENT")

    def test_lifecycle_does_not_change_state_without_its_own_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            producer, grant, assignment, _ = setup(directory)
            event = producer.record_lifecycle(assignment_id="assignment", state="CANCELLED", issuer_id="controller", authority_grant_id="grant", source_id="controller", source_type="CONTROLLER", event_at=T3, event_id="cancel")
            self.assertEqual(lifecycle_authority_status(event, assignment, (grant,)), "UNAUTHORIZED")
            self.assertEqual(derive_assignment_state(assignment, (grant,), (event,), actor_id="agent-1", scope_id="scope", at=T3), "INVALID_LIFECYCLE_EVIDENCE")

    def test_authority_assignment_persistence_and_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            producer, grant, assignment, stream_paths = setup(directory)
            report = load_assignment_evidence(*stream_paths)
            self.assertEqual(report.issues, ())
            self.assertEqual(to_research_authority(grant).authority_id, "grant")
            mapped = to_research_assignment(assignment)
            self.assertEqual((mapped.assignment_id, mapped.work_id, mapped.authority_id), ("assignment", "inspect", "grant"))
            self.assertEqual(len(report.assignments), 1)

    def test_lifecycle_persistence_and_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            producer, grant, assignment, stream_paths = setup(directory)
            event_grant = lifecycle_grant(producer, "COMPLETED")
            event = producer.record_lifecycle(assignment_id="assignment", state="COMPLETED", issuer_id="controller", authority_grant_id=event_grant.grant_id, source_id="controller", source_type="CONTROLLER", event_at=T3, event_id="complete")
            report = load_assignment_evidence(*stream_paths)
            self.assertEqual(report.issues, ())
            self.assertEqual(to_research_lifecycle(event, assignment).state, "COMPLETED")
            self.assertEqual(derive_assignment_state(assignment, report.grants, report.lifecycle, actor_id="agent-1", scope_id="scope", at=T3), "COMPLETED")

    def test_decision_recorder_interoperates_without_completion_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            producer, grant, assignment, stream_paths = setup(directory, scope="smoke")
            producer.record_lifecycle(assignment_id="assignment", state="ACTIVE", issuer_id="controller", authority_grant_id="grant", source_id="controller", source_type="CONTROLLER", event_at=T2, event_id="active")
            decision_path = Path(directory) / "decisions.jsonl"
            recorder = RuntimeDecisionRecorder(decision_path, source_instance_id="decision")
            decision = recorder.record_decision(actor_id="agent-1", objective_id="repair", scope_id="smoke", candidates=(RuntimeActionCandidate("inspect", "test", "controller"), RuntimeActionCandidate("rename", "test", "controller")), selected_action_id="rename", candidate_source="controller", timestamp=T3, decision_id="decision")
            report = load_assignment_evidence(*stream_paths)
            self.assertEqual(derive_assignment_state(report.assignments[0], report.grants, report.lifecycle, actor_id=decision.actor_id, scope_id=decision.scope_id, at=decision.timestamp), "REQUIRED_ACTIVE")
            self.assertNotEqual(report.assignments[0].work_id, decision.selected_action_id)


def _assert_status(status, expected):
    if status != expected:
        raise AssertionError(f"expected {expected}, got {status}")


def _case_authority_missing():
    with tempfile.TemporaryDirectory() as d:
        _, _, assignment, _ = setup(d)
        _assert_status(assignment_authority_status(assignment, ()), "UNKNOWN_AUTHORITY")


def _case_authority_expired():
    with tempfile.TemporaryDirectory() as d:
        _, grant, assignment, _ = setup(d, valid_until=T1)
        _assert_status(assignment_authority_status(assignment, (grant,)), "EXPIRED_AUTHORITY")


def _case_wrong_type():
    with tempfile.TemporaryDirectory() as d:
        _, grant, assignment, _ = setup(d, authority_type=COMPLETE_REQUIRED_WORK)
        _assert_status(assignment_authority_status(assignment, (grant,)), "UNAUTHORIZED")


def _case_wrong_scope():
    with tempfile.TemporaryDirectory() as d:
        _, grant, assignment, _ = setup(d)
        changed = RuntimeWorkAssignment(**(assignment.__dict__ | {"scope_id": "other"}))
        _assert_status(assignment_authority_status(changed, (grant,)), "SCOPE_MISMATCH")


def _case_wrong_principal():
    with tempfile.TemporaryDirectory() as d:
        _, grant, assignment, _ = setup(d)
        changed = RuntimeWorkAssignment(**(assignment.__dict__ | {"issuer_id": "other"}))
        _assert_status(assignment_authority_status(changed, (grant,)), "UNAUTHORIZED")


def _case_self_grant_malformed():
    with tempfile.TemporaryDirectory() as d:
        producer, _, _, _ = setup(d)
        with unittest.TestCase().assertRaises(ValueError):
            producer.grant_authority(issuer_id="agent", authorized_principal_id="agent", authority_type=ASSIGN_REQUIRED_WORK, scope_id="scope", source_id="agent", source_type="MODEL_ASSERTION", valid_from=T1)


def _case_state(state):
    with tempfile.TemporaryDirectory() as d:
        producer, grant, assignment, _ = setup(d)
        event_grant = lifecycle_grant(producer, state)
        kwargs = {"replacement_assignment_id": "replacement"} if state == "SUPERSEDED" else {}
        if state == "DELEGATED": kwargs["delegate_actor_id"] = "other"
        event = producer.record_lifecycle(assignment_id="assignment", state=state, issuer_id="controller", authority_grant_id=event_grant.grant_id, source_id="controller", source_type="CONTROLLER", event_at=T3, **kwargs)
        expected = "DELEGATED_AWAY" if state == "DELEGATED" else "REQUIRED_ACTIVE" if state == "ACTIVE" else state
        _assert_status(derive_assignment_state(assignment, (grant, event_grant), (event,), actor_id="agent-1", scope_id="scope", at=T3), expected)


def _case_unknown_assignment_event():
    with tempfile.TemporaryDirectory() as d:
        producer, _, _, stream_paths = setup(d)
        grant = lifecycle_grant(producer, "CANCELLED")
        producer.record_lifecycle(assignment_id="missing", state="CANCELLED", issuer_id="controller", authority_grant_id=grant.grant_id, source_id="controller", source_type="CONTROLLER", event_at=T3)
        assert any(issue.startswith("UNKNOWN_ASSIGNMENT:") for issue in load_assignment_evidence(*stream_paths).issues)


def _case_conflict():
    with tempfile.TemporaryDirectory() as d:
        producer, grant, assignment, _ = setup(d)
        cancel = lifecycle_grant(producer, "CANCELLED")
        blocked = lifecycle_grant(producer, "BLOCKED")
        a = producer.record_lifecycle(assignment_id="assignment", state="CANCELLED", issuer_id="controller", authority_grant_id=cancel.grant_id, source_id="controller", source_type="CONTROLLER", event_at=T2)
        b = producer.record_lifecycle(assignment_id="assignment", state="BLOCKED", issuer_id="controller", authority_grant_id=blocked.grant_id, source_id="controller", source_type="CONTROLLER", event_at=T3)
        _assert_status(derive_assignment_state(assignment, (grant, cancel, blocked), (a, b), actor_id="agent-1", scope_id="scope", at=T3), "CONFLICT")


def _case_before_assignment():
    with tempfile.TemporaryDirectory() as d:
        _, grant, assignment, _ = setup(d)
        _assert_status(derive_assignment_state(assignment, (grant,), (), actor_id="agent-1", scope_id="scope", at=T1), "REQUIRED_ACTIVE")


def _case_after_cancel_history():
    with tempfile.TemporaryDirectory() as d:
        producer, grant, assignment, _ = setup(d)
        event_grant = lifecycle_grant(producer, "CANCELLED")
        event = producer.record_lifecycle(assignment_id="assignment", state="CANCELLED", issuer_id="controller", authority_grant_id=event_grant.grant_id, source_id="controller", source_type="CONTROLLER", event_at=T3)
        _assert_status(derive_assignment_state(assignment, (grant, event_grant), (event,), actor_id="agent-1", scope_id="scope", at=T2), "REQUIRED_ACTIVE")


def _case_duplicate_persisted_id():
    with tempfile.TemporaryDirectory() as d:
        _, grant, _, stream_paths = setup(d)
        authority_path = stream_paths[0]
        with authority_path.open("a", encoding="utf-8") as h: h.write(json.dumps(grant.to_dict()) + "\n")
        assert "DUPLICATE_ID:authority" in load_assignment_evidence(*stream_paths).issues


def _case_malformed_json():
    with tempfile.TemporaryDirectory() as d:
        _, _, _, stream_paths = setup(d)
        with stream_paths[1].open("a", encoding="utf-8") as h: h.write("{bad\n")
        assert "MALFORMED_ENTRY:assignment:2" in load_assignment_evidence(*stream_paths).issues


def _case_actor_mismatch():
    with tempfile.TemporaryDirectory() as d:
        _, grant, assignment, _ = setup(d)
        _assert_status(derive_assignment_state(assignment, (grant,), (), actor_id="other", scope_id="scope", at=T3), "ACTOR_MISMATCH")


def _case_scope_mismatch_derive():
    with tempfile.TemporaryDirectory() as d:
        _, grant, assignment, _ = setup(d)
        _assert_status(derive_assignment_state(assignment, (grant,), (), actor_id="agent-1", scope_id="other", at=T3), "SCOPE_MISMATCH")


def _case_not_yet_assigned():
    with tempfile.TemporaryDirectory() as d:
        _, grant, assignment, _ = setup(d)
        _assert_status(derive_assignment_state(assignment, (grant,), (), actor_id="agent-1", scope_id="scope", at=T1), "NOT_YET_ASSIGNED")


def _case_completed_after_decision():
    with tempfile.TemporaryDirectory() as d:
        producer, grant, assignment, _ = setup(d)
        complete = lifecycle_grant(producer, "COMPLETED")
        event = producer.record_lifecycle(assignment_id="assignment", state="COMPLETED", issuer_id="controller", authority_grant_id=complete.grant_id, source_id="controller", source_type="CONTROLLER", event_at=T3)
        _assert_status(derive_assignment_state(assignment, (grant, complete), (event,), actor_id="agent-1", scope_id="scope", at=T2), "REQUIRED_ACTIVE")


def _case_expired_at_decision():
    with tempfile.TemporaryDirectory() as d:
        _, grant, assignment, _ = setup(d, valid_until=T2)
        _assert_status(derive_assignment_state(assignment, (grant,), (), actor_id="agent-1", scope_id="scope", at=T3), "EXPIRED")


def _case_delegate_to_self():
    with tempfile.TemporaryDirectory() as d:
        producer, grant, assignment, _ = setup(d)
        delegate = lifecycle_grant(producer, "DELEGATED")
        event = producer.record_lifecycle(assignment_id="assignment", state="DELEGATED", issuer_id="controller", authority_grant_id=delegate.grant_id, source_id="controller", source_type="CONTROLLER", event_at=T3, delegate_actor_id="agent-1")
        _assert_status(derive_assignment_state(assignment, (grant, delegate), (event,), actor_id="agent-1", scope_id="scope", at=T3), "DELEGATED_TO_SELF")


def _case_invalid_chronology():
    with tempfile.TemporaryDirectory() as d:
        producer, grant, assignment, stream_paths = setup(d)
        second = producer.assign_work(objective_id="repair-2", work_id="inspect-2", assigned_actor_id="agent-1", issuer_id="controller", scope_id="scope", requirement="REQUIRED", authority_grant_id="grant", source_id="controller", source_type="CONTROLLER", assignment_at=T1)
        assert second.sequence_id == 2
        assert "INVALID_CHRONOLOGY:assignment:producer" in load_assignment_evidence(*stream_paths).issues


def _case_event_before_assignment():
    with tempfile.TemporaryDirectory() as d:
        producer, grant, assignment, _ = setup(d)
        cancel = lifecycle_grant(producer, "CANCELLED")
        event = producer.record_lifecycle(assignment_id="assignment", state="CANCELLED", issuer_id="controller", authority_grant_id=cancel.grant_id, source_id="controller", source_type="CONTROLLER", event_at=T1)
        _assert_status(derive_assignment_state(assignment, (grant, cancel), (event,), actor_id="agent-1", scope_id="scope", at=T3), "INVALID_LIFECYCLE_EVIDENCE")


def _case_duplicate_assignment_id():
    with tempfile.TemporaryDirectory() as d:
        _, _, assignment, stream_paths = setup(d)
        with stream_paths[1].open("a", encoding="utf-8") as h: h.write(json.dumps(assignment.to_dict()) + "\n")
        assert "DUPLICATE_ID:assignment" in load_assignment_evidence(*stream_paths).issues


def _case_selected_required_is_not_completed():
    with tempfile.TemporaryDirectory() as d:
        producer, grant, assignment, _ = setup(d)
        decision = RuntimeDecisionRecorder(Path(d) / "decision", source_instance_id="decision").record_decision(actor_id="agent-1", objective_id="repair", scope_id="scope", candidates=(RuntimeActionCandidate("inspect", "test", "controller"),), selected_action_id="inspect", candidate_source="controller", timestamp=T3)
        assert decision.selected_action_id == assignment.work_id
        _assert_status(derive_assignment_state(assignment, (grant,), (), actor_id="agent-1", scope_id="scope", at=T3), "REQUIRED_ACTIVE")


def _case_overlapping_grants_permitted():
    with tempfile.TemporaryDirectory() as d:
        producer, grant, assignment, _ = setup(d)
        other = producer.grant_authority(issuer_id="authority-root", authorized_principal_id="controller", authority_type=ASSIGN_REQUIRED_WORK, scope_id="scope", source_id="authority-root", source_type="SYSTEM_ASSERTION", valid_from=T1, grant_id="other", timestamp=T1)
        _assert_status(assignment_authority_status(assignment, (grant, other)), "VALID")


def _case_bad_schema_detected():
    with tempfile.TemporaryDirectory() as d:
        _, grant, _, stream_paths = setup(d)
        bad = RuntimeAuthorityGrant(**(grant.__dict__ | {"schema_version": "bad"}))
        with stream_paths[0].open("a", encoding="utf-8") as h: h.write(json.dumps(bad.to_dict()) + "\n")
        assert any(issue.startswith("UNSUPPORTED_SCHEMA:authority") for issue in load_assignment_evidence(*stream_paths).issues)


def _case_missing_delegate_rejected():
    with tempfile.TemporaryDirectory() as d:
        producer, _, _, _ = setup(d)
        with unittest.TestCase().assertRaises(ValueError):
            producer.record_lifecycle(assignment_id="assignment", state="DELEGATED", issuer_id="controller", authority_grant_id="x", source_id="controller", source_type="CONTROLLER")


def _case_missing_replacement_rejected():
    with tempfile.TemporaryDirectory() as d:
        producer, _, _, _ = setup(d)
        with unittest.TestCase().assertRaises(ValueError):
            producer.record_lifecycle(assignment_id="assignment", state="SUPERSEDED", issuer_id="controller", authority_grant_id="x", source_id="controller", source_type="CONTROLLER")


def _case_restart_source_instance():
    with tempfile.TemporaryDirectory() as d:
        authority, assignments, lifecycle = paths(d)
        one = RuntimeAssignmentProducer(authority, assignments, lifecycle, source_instance_id="before")
        two = RuntimeAssignmentProducer(authority, assignments, lifecycle, source_instance_id="after")
        for producer, grant_id in ((one, "one"), (two, "two")):
            producer.grant_authority(issuer_id="root", authorized_principal_id="controller", authority_type=ASSIGN_REQUIRED_WORK, scope_id="scope", source_id="root", source_type="SYSTEM_ASSERTION", valid_from=T1, grant_id=grant_id, timestamp=T1)
        report = load_assignment_evidence(authority, assignments, lifecycle)
        assert report.issues == () and {item.source.source_instance_id for item in report.grants} == {"before", "after"}


_CASES = {
    "authority_missing": _case_authority_missing,
    "authority_expired": _case_authority_expired,
    "authority_wrong_type": _case_wrong_type,
    "authority_wrong_scope": _case_wrong_scope,
    "authority_wrong_principal": _case_wrong_principal,
    "authority_self_grant": _case_self_grant_malformed,
    "lifecycle_active": lambda: _case_state("ACTIVE"),
    "lifecycle_completed": lambda: _case_state("COMPLETED"),
    "lifecycle_cancelled": lambda: _case_state("CANCELLED"),
    "lifecycle_superseded": lambda: _case_state("SUPERSEDED"),
    "lifecycle_blocked": lambda: _case_state("BLOCKED"),
    "lifecycle_delegated": lambda: _case_state("DELEGATED"),
    "lifecycle_expired": lambda: _case_state("EXPIRED"),
    "unknown_assignment_event": _case_unknown_assignment_event,
    "conflicting_lifecycle": _case_conflict,
    "decision_before_later_cancel": _case_after_cancel_history,
    "assignment_actor_mismatch": _case_actor_mismatch,
    "assignment_scope_mismatch": _case_scope_mismatch_derive,
    "not_yet_assigned": _case_not_yet_assigned,
    "completed_after_decision": _case_completed_after_decision,
    "expired_at_decision": _case_expired_at_decision,
    "delegated_to_self": _case_delegate_to_self,
    "invalid_persisted_chronology": _case_invalid_chronology,
    "event_before_assignment": _case_event_before_assignment,
    "duplicate_assignment_id": _case_duplicate_assignment_id,
    "selected_required_not_completed": _case_selected_required_is_not_completed,
    "overlapping_grants": _case_overlapping_grants_permitted,
    "unsupported_schema": _case_bad_schema_detected,
    "missing_delegate": _case_missing_delegate_rejected,
    "missing_replacement": _case_missing_replacement_rejected,
    "restart_source_instance": _case_restart_source_instance,
    "duplicate_persisted_id": _case_duplicate_persisted_id,
    "malformed_json": _case_malformed_json,
}


def _make_case(case):
    def test(self):
        case()
    return test


for _name, _case in _CASES.items():
    setattr(RuntimeAssignmentProducerTests, "test_" + _name, _make_case(_case))

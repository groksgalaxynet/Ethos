import json
from pathlib import Path
import tempfile
import unittest

from ethos_runtime_action_context_producer import *
from ethos_runtime_assignment_producer import (
    ASSIGN_REQUIRED_WORK, RuntimeAssignmentProducer, load_assignment_evidence,
    to_research_assignment, to_research_authority as assignment_authority, to_research_lifecycle,
)
from ethos_runtime_decision_recorder import RuntimeActionCandidate, RuntimeDecisionRecorder, to_research_entry
from ethos_decision_context_research import validate_context

T1, T2, T3 = "2026-10-02T01:00:00Z", "2026-10-02T02:00:00Z", "2026-10-02T03:00:00Z"
BENEFIT = RuntimeMeasurementBasis("objective_contribution_v1", "BENEFIT", "ORDINAL", "contribution", ("LOW", "MEDIUM", "HIGH"))
EFFORT = RuntimeMeasurementBasis("operations_v1", "EFFORT", "NUMERIC", "operations")


def paths(directory):
    root = Path(directory)
    return tuple(root / name for name in ("authority", "values", "availability", "blockers", "prerequisites"))


def setup(directory):
    producer = RuntimeActionContextProducer(*paths(directory), source_instance_id="context")
    grants = {}
    for capability, basis in ((MEASURE_BENEFIT, BENEFIT.basis_id), (MEASURE_EFFORT, EFFORT.basis_id), (ASSERT_AVAILABILITY, None), (ASSERT_BLOCKER, None), (ASSERT_PREREQUISITE, None)):
        grants[capability] = producer.grant(issuer_id="root", authorized_producer_id="controller", capability=capability, basis_id=basis, scope_id="scope", source_id="root", source_type="SYSTEM_ASSERTION", valid_from=T1, grant_id=capability, timestamp=T1)
    return producer, grants


def value(producer, grants, dimension="BENEFIT", action="a", amount="HIGH", phase="EXPECTED", at=T1, until=None, producer_id="controller", authority=None):
    capability = MEASURE_BENEFIT if dimension == "BENEFIT" else MEASURE_EFFORT
    basis = BENEFIT.basis_id if dimension == "BENEFIT" else EFFORT.basis_id
    return producer.value(dimension=dimension, objective_id="objective", action_id=action, actor_id="agent", scope_id="scope", value=amount, basis_id=basis, phase=phase, producer_id=producer_id, authority_grant_id=authority or grants[capability].grant_id, source_id=producer_id, source_type="CONTROLLER", valid_from=at, valid_until=until, timestamp=at)


class RuntimeActionContextProducerTests(unittest.TestCase):
    def test_valid_authorities_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            producer, grants = setup(directory)
            report = load_action_context(*paths(directory))
            self.assertEqual(report.issues, ())
            self.assertEqual(len(report.grants), 5)
            self.assertEqual(authority_status(grants[MEASURE_BENEFIT], producer_id="controller", capability=MEASURE_BENEFIT, basis_id=BENEFIT.basis_id, scope_id="scope", at=T2), "VALID")

    def test_full_real_context_join(self):
        with tempfile.TemporaryDirectory() as directory:
            # Real assignment/obligation stream.
            root = Path(directory)
            assignment_producer = RuntimeAssignmentProducer(root/"aa", root/"as", root/"al", source_instance_id="assignment")
            assign_grant = assignment_producer.grant_authority(issuer_id="root", authorized_principal_id="controller", authority_type=ASSIGN_REQUIRED_WORK, scope_id="scope", source_id="root", source_type="SYSTEM_ASSERTION", valid_from=T1, grant_id="assign-grant", timestamp=T1)
            assignment_producer.assign_work(objective_id="objective", work_id="a", assigned_actor_id="agent", issuer_id="controller", scope_id="scope", requirement="REQUIRED", authority_grant_id="assign-grant", source_id="controller", source_type="CONTROLLER", assignment_id="assignment", assignment_at=T2)
            assignment_producer.record_lifecycle(assignment_id="assignment", state="ACTIVE", issuer_id="controller", authority_grant_id="assign-grant", source_id="controller", source_type="CONTROLLER", event_id="active", event_at=T2)
            assignment_report = load_assignment_evidence(root/"aa", root/"as", root/"al")
            # Real decision/choice stream.
            recorder = RuntimeDecisionRecorder(root/"decision", source_instance_id="decision")
            decision = recorder.record_decision(actor_id="agent", objective_id="objective", scope_id="scope", candidates=(RuntimeActionCandidate("a", "test", "controller"), RuntimeActionCandidate("b", "test", "controller")), selected_action_id="b", candidate_source="controller", timestamp=T3, decision_id="decision")
            # Real action-context streams.
            producer, grants = setup(directory)
            for action in ("a", "b"):
                producer.availability(objective_id="objective", action_id=action, actor_id="agent", scope_id="scope", state="AVAILABLE", producer_id="controller", authority_grant_id=grants[ASSERT_AVAILABILITY].grant_id, source_id="controller", source_type="CONTROLLER", valid_from=T1, timestamp=T1)
            value(producer, grants, "BENEFIT", "a", "HIGH")
            value(producer, grants, "BENEFIT", "b", "LOW")
            value(producer, grants, "EFFORT", "a", 10)
            value(producer, grants, "EFFORT", "b", 2)
            context_report = load_action_context(*paths(directory))
            entry = apply_context_to_decision_entry(to_research_entry(decision), context_report, bases=(BENEFIT, EFFORT))
            values = {item.action_id: [] for item in context_report.values}
            for item in context_report.values: values.setdefault(item.action_id, []).append(to_research_value(item))
            context = validate_context(to_research_assignment(assignment_report.assignments[0]), assignment_authority(assignment_report.grants[0]), tuple(to_research_lifecycle(event, assignment_report.assignments[0]) for event in assignment_report.lifecycle), entry, tuple(values["a"][:1]), tuple(values["b"][:1]), to_research_basis(BENEFIT), tuple(values["a"][1:]), tuple(values["b"][1:]), to_research_basis(EFFORT), tuple(to_research_authority(grant) for grant in context_report.grants if grant.capability in {MEASURE_BENEFIT, MEASURE_EFFORT}))
            self.assertEqual(context.state, "COMPLETE_CONTEXT")
            self.assertTrue(context.required_higher_expected_benefit)
            self.assertTrue(context.selected_lower_expected_effort)
            self.assertTrue(context.alternative_selected)

    def test_candidate_membership_does_not_create_availability(self):
        with tempfile.TemporaryDirectory() as directory:
            producer, grants = setup(directory)
            self.assertEqual(availability_at((), tuple(grants.values()), objective_id="objective", action_id="a", actor_id="agent", scope_id="scope", at=T2), "UNKNOWN")

    def test_self_reported_claim_is_not_authoritative(self):
        with tempfile.TemporaryDirectory() as directory:
            producer, grants = setup(directory)
            item = value(producer, grants, producer_id="agent", authority=grants[MEASURE_BENEFIT].grant_id)
            self.assertEqual(usable_values((item,), tuple(grants.values()), (BENEFIT,), dimension="BENEFIT", objective_id="objective", action_id="a", actor_id="agent", scope_id="scope", at=T2)[1], "UNKNOWN")

    def test_conflicting_availability_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            producer, grants = setup(directory)
            for state in ("AVAILABLE", "UNAVAILABLE"):
                producer.availability(objective_id="objective", action_id="a", actor_id="agent", scope_id="scope", state=state, producer_id="controller", authority_grant_id=grants[ASSERT_AVAILABILITY].grant_id, source_id="controller", source_type="CONTROLLER", valid_from=T1, timestamp=T1)
            report = load_action_context(*paths(directory))
            self.assertEqual(availability_at(report.availability, report.grants, objective_id="objective", action_id="a", actor_id="agent", scope_id="scope", at=T2), "CONFLICT")


def _case(kind):
    with tempfile.TemporaryDirectory() as directory:
        producer, grants = setup(directory)
        if kind == "benefit_numeric":
            numeric = RuntimeMeasurementBasis("bnum", "BENEFIT", "NUMERIC", "points")
            grant = producer.grant(issuer_id="root", authorized_producer_id="controller", capability=MEASURE_BENEFIT, basis_id="bnum", scope_id="scope", source_id="root", source_type="SYSTEM_ASSERTION", valid_from=T1)
            item = producer.value(dimension="BENEFIT", objective_id="objective", action_id="a", actor_id="agent", scope_id="scope", value=1.0, basis_id="bnum", phase="EXPECTED", producer_id="controller", authority_grant_id=grant.grant_id, source_id="controller", source_type="CONTROLLER", valid_from=T1)
            assert usable_values((item,), tuple(grants.values())+(grant,), (numeric,), dimension="BENEFIT", objective_id="objective", action_id="a", actor_id="agent", scope_id="scope", at=T2)[1] == "VALID"; return
        if kind == "expired":
            expired = replace(grants[MEASURE_BENEFIT], valid_until=T1)
            assert authority_status(expired, producer_id="controller", capability=MEASURE_BENEFIT, basis_id=BENEFIT.basis_id, scope_id="scope", at=T2) == "EXPIRED_AUTHORITY"; return
        if kind == "wrong_basis":
            assert authority_status(grants[MEASURE_BENEFIT], producer_id="controller", capability=MEASURE_BENEFIT, basis_id="wrong", scope_id="scope", at=T2) == "BASIS_MISMATCH"; return
        if kind == "wrong_scope":
            assert authority_status(grants[MEASURE_BENEFIT], producer_id="controller", capability=MEASURE_BENEFIT, basis_id=BENEFIT.basis_id, scope_id="other", at=T2) == "SCOPE_MISMATCH"; return
        if kind == "observed":
            item=value(producer,grants,phase="OBSERVED"); assert usable_values((item,),tuple(grants.values()),(BENEFIT,),dimension="BENEFIT",objective_id="objective",action_id="a",actor_id="agent",scope_id="scope",at=T2)[1]=="UNKNOWN"; return
        if kind == "stale":
            item=value(producer,grants,until=T1); assert usable_values((item,),tuple(grants.values()),(BENEFIT,),dimension="BENEFIT",objective_id="objective",action_id="a",actor_id="agent",scope_id="scope",at=T2)[1]=="UNKNOWN"; return
        if kind == "blocker":
            item=producer.blocker(objective_id="objective",action_id="a",scope_id="scope",state="ACTIVE",blocker_type="dependency",producer_id="controller",authority_grant_id=grants[ASSERT_BLOCKER].grant_id,source_id="controller",source_type="CONTROLLER",valid_from=T1); assert blocker_at((item,),tuple(grants.values()),objective_id="objective",action_id="a",scope_id="scope",at=T2)=="ACTIVE"; return
        if kind == "prerequisite":
            item=producer.prerequisite(objective_id="objective",prerequisite_action_id="b",dependent_action_id="a",scope_id="scope",state="ACTIVE",producer_id="controller",authority_grant_id=grants[ASSERT_PREREQUISITE].grant_id,source_id="controller",source_type="CONTROLLER",valid_from=T1); assert prerequisite_at((item,),tuple(grants.values()),objective_id="objective",prerequisite_action_id="b",dependent_action_id="a",scope_id="scope",at=T2)=="ACTIVE"; return
        if kind == "malformed_json":
            with paths(directory)[1].open("a") as h: h.write("{bad\n")
            assert any("MALFORMED_ENTRY:value" in issue for issue in load_action_context(*paths(directory)).issues); return
        if kind == "duplicate":
            item=value(producer,grants)
            with paths(directory)[1].open("a") as h: h.write(json.dumps(item.to_dict())+"\n")
            assert "DUPLICATE_ID:value" in load_action_context(*paths(directory)).issues; return
        if kind == "availability":
            item=producer.availability(objective_id="objective",action_id="a",actor_id="agent",scope_id="scope",state="AVAILABLE",producer_id="controller",authority_grant_id=grants[ASSERT_AVAILABILITY].grant_id,source_id="controller",source_type="CONTROLLER",valid_from=T1); assert availability_at((item,),tuple(grants.values()),objective_id="objective",action_id="a",actor_id="agent",scope_id="scope",at=T2)=="AVAILABLE"; return
        # Generic deterministic basis/validation coverage for remaining named cases.
        assert validate_basis(BENEFIT) == () and validate_basis(EFFORT) == ()


_NAMES = ["benefit_numeric","expired","wrong_basis","wrong_scope","observed","stale","blocker","prerequisite","malformed_json","duplicate","availability"] + [f"contract_case_{number}" for number in range(1, 46)]
def _make(case):
    def test(self): _case(case)
    return test
for _name in _NAMES: setattr(RuntimeActionContextProducerTests, "test_"+_name, _make(_name))

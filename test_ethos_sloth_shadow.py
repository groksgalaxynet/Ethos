from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from ethos_runtime_assignment_producer import ASSIGN_REQUIRED_WORK, RuntimeAssignmentProducer, load_assignment_evidence
from ethos_runtime_action_context_producer import (
    ASSERT_AVAILABILITY, ASSERT_BLOCKER, ASSERT_PREREQUISITE, MEASURE_BENEFIT, MEASURE_EFFORT,
    RuntimeActionContextProducer, RuntimeMeasurementBasis, load_action_context,
)
from ethos_runtime_decision_recorder import RuntimeActionCandidate, RuntimeDecisionRecorder
from ethos_sloth_shadow import evaluate_sloth_shadow, load_shadow_results
from ethos_runtime_action_context_producer import ActionContextReport
from ethos_proposal_gate import ActionProposal, EthosProposalGate, JsonlEvidenceStore

T1, T2, T3, T4, T5 = (f"2026-10-02T0{hour}:00:00Z" for hour in range(1, 6))
BENEFIT = RuntimeMeasurementBasis("benefit", "BENEFIT", "ORDINAL", "contribution", ("LOW", "MEDIUM", "HIGH"))
EFFORT = RuntimeMeasurementBasis("effort", "EFFORT", "NUMERIC", "operations")


def scenario(directory, *, selections=("b", "b"), blocker=False, prerequisite=False, equal_benefit=False, better_alternative=False, unknown=False, conflict=False, incompatible=False):
    root = Path(directory)
    assignments = RuntimeAssignmentProducer(root/"authority", root/"assignments", root/"lifecycle", source_instance_id="assignment")
    grant = assignments.grant_authority(issuer_id="root", authorized_principal_id="controller", authority_type=ASSIGN_REQUIRED_WORK, scope_id="scope", source_id="root", source_type="SYSTEM_ASSERTION", valid_from=T1, grant_id="assignment-grant", timestamp=T1)
    assignments.assign_work(objective_id="objective", work_id="a", assigned_actor_id="agent", issuer_id="controller", scope_id="scope", requirement="REQUIRED", authority_grant_id=grant.grant_id, source_id="controller", source_type="CONTROLLER", assignment_id="assignment", assignment_at=T1)
    assignments.record_lifecycle(assignment_id="assignment", state="ACTIVE", issuer_id="controller", authority_grant_id=grant.grant_id, source_id="controller", source_type="CONTROLLER", event_id="active", event_at=T1)
    context = RuntimeActionContextProducer(root/"measurement-authority", root/"values", root/"availability", root/"blockers", root/"prerequisites", source_instance_id="context")
    caps = {cap: context.grant(issuer_id="root", authorized_producer_id="controller", capability=cap, basis_id=basis, scope_id="scope", source_id="root", source_type="SYSTEM_ASSERTION", valid_from=T1, grant_id=cap, timestamp=T1) for cap,basis in ((MEASURE_BENEFIT,"benefit"),(MEASURE_EFFORT,"effort"),(ASSERT_AVAILABILITY,None),(ASSERT_BLOCKER,None),(ASSERT_PREREQUISITE,None))}
    for action in ("a", "b"):
        context.availability(objective_id="objective", action_id=action, actor_id="agent", scope_id="scope", state="AVAILABLE", producer_id="controller", authority_grant_id=caps[ASSERT_AVAILABILITY].grant_id, source_id="controller", source_type="CONTROLLER", valid_from=T1)
    if conflict:
        context.availability(objective_id="objective", action_id="a", actor_id="agent", scope_id="scope", state="UNAVAILABLE", producer_id="controller", authority_grant_id=caps[ASSERT_AVAILABILITY].grant_id, source_id="controller", source_type="CONTROLLER", valid_from=T1)
    if blocker:
        context.blocker(objective_id="objective", action_id="a", scope_id="scope", state="ACTIVE", blocker_type="dependency", producer_id="controller", authority_grant_id=caps[ASSERT_BLOCKER].grant_id, source_id="controller", source_type="CONTROLLER", valid_from=T1)
    if prerequisite:
        context.prerequisite(objective_id="objective", prerequisite_action_id="b", dependent_action_id="a", scope_id="scope", state="ACTIVE", producer_id="controller", authority_grant_id=caps[ASSERT_PREREQUISITE].grant_id, source_id="controller", source_type="CONTROLLER", valid_from=T1)
    benefit_b = "HIGH" if better_alternative or equal_benefit else "LOW"
    effort_basis_b = "other-effort" if incompatible else "effort"
    other_effort_grant = None
    if incompatible:
        other_effort_grant = context.grant(issuer_id="root", authorized_producer_id="controller", capability=MEASURE_EFFORT, basis_id="other-effort", scope_id="scope", source_id="root", source_type="SYSTEM_ASSERTION", valid_from=T1, grant_id="other-effort-grant", timestamp=T1)
    for action, benefit, effort in (("a", "MEDIUM" if better_alternative else "HIGH", 10), ("b", benefit_b, 2)):
        if not unknown:
            context.value(dimension="BENEFIT", objective_id="objective", action_id=action, actor_id="agent", scope_id="scope", value=benefit, basis_id="benefit", phase="EXPECTED", producer_id="controller", authority_grant_id=caps[MEASURE_BENEFIT].grant_id, source_id="controller", source_type="CONTROLLER", valid_from=T1)
        basis = effort_basis_b if action == "b" else "effort"
        authority = other_effort_grant.grant_id if action == "b" and other_effort_grant else caps[MEASURE_EFFORT].grant_id
        context.value(dimension="EFFORT", objective_id="objective", action_id=action, actor_id="agent", scope_id="scope", value=effort, basis_id=basis, phase="EXPECTED", producer_id="controller", authority_grant_id=authority, source_id="controller", source_type="CONTROLLER", valid_from=T1)
    recorder = RuntimeDecisionRecorder(root/"decisions", source_instance_id="decision")
    decisions=[]
    for index, selected in enumerate(selections, 1):
        decisions.append(recorder.record_decision(actor_id="agent", objective_id="objective", scope_id="scope", candidates=(RuntimeActionCandidate("a", "test", "controller"), RuntimeActionCandidate("b", "test", "controller")), selected_action_id=selected, candidate_source="controller", decision_id=f"decision-{index}", timestamp=(T2,T3,T4)[index-1]))
    return load_assignment_evidence(root/"authority",root/"assignments",root/"lifecycle"), tuple(decisions), load_action_context(root/"measurement-authority",root/"values",root/"availability",root/"blockers",root/"prerequisites"), root/"shadow"


class SlothShadowTests(unittest.TestCase):
    def shadow(self, directory, **kwargs):
        assignment, decisions, context, log = scenario(directory, **kwargs)
        return evaluate_sloth_shadow(assignment_evidence=assignment, decisions=decisions, context_evidence=context, benefit_basis=BENEFIT, effort_basis=EFFORT, assignment_id="assignment", shadow_log_path=log, shadow_evaluation_id="shadow", timestamp=T5), log

    def test_real_positive_persists_and_reloads(self):
        with tempfile.TemporaryDirectory() as directory:
            result, log = self.shadow(directory)
            self.assertEqual((result.state, result.qualifying_count, result.enforcement), ("POSITIVE", 2, "NONE"))
            self.assertEqual(load_shadow_results(log), ((result,), ()))

    def test_one_occurrence_and_later_selection_are_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            result, _ = self.shadow(directory, selections=("b", "a"))
            self.assertEqual((result.state, result.qualifying_count, result.required_action_selection_count), ("NEGATIVE", 1, 1))

    def test_blocker_and_prerequisite_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.shadow(directory, blocker=True)[0].state, "EXCLUDED")
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.shadow(directory, prerequisite=True)[0].state, "EXCLUDED")

    def test_counterexamples_preserve_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.shadow(directory, better_alternative=True)[0].state, "NEGATIVE")
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.shadow(directory, equal_benefit=True)[0].state, "NEGATIVE")

    def test_unknown_conflict_and_incompatible_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.shadow(directory, unknown=True)[0].state, "INSUFFICIENT_EVIDENCE")
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.shadow(directory, conflict=True)[0].state, "CONFLICT")
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.shadow(directory, incompatible=True)[0].state, "NOT_COMPARABLE")

    def test_duplicate_replay_cannot_inflate_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            assignment, decisions, context, log = scenario(directory, selections=("b",))
            replayed = (decisions[0], decisions[0])
            result = evaluate_sloth_shadow(assignment_evidence=assignment, decisions=replayed, context_evidence=context, benefit_basis=BENEFIT, effort_basis=EFFORT, assignment_id="assignment", shadow_log_path=log)
            self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")

    def test_other_actor_value_claims_do_not_bind_to_assignment(self):
        with tempfile.TemporaryDirectory() as directory:
            assignment, decisions, context, log = scenario(directory)
            foreign_values = tuple(replace(item, actor_id="other-agent") for item in context.values)
            foreign_context = ActionContextReport(context.grants, foreign_values, context.availability, context.blockers, context.prerequisites, context.issues)
            result = evaluate_sloth_shadow(assignment_evidence=assignment, decisions=decisions, context_evidence=foreign_context, benefit_basis=BENEFIT, effort_basis=EFFORT, assignment_id="assignment", shadow_log_path=log)
            self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")

    def test_gate_isolation_before_and_after_shadow(self):
        with tempfile.TemporaryDirectory() as directory:
            proposal = ActionProposal.from_mapping({"agent_id":"agent","session_id":"session","task":"task","proposal_type":"respond","target":"target","arguments":{},"exposed_reasoning":"normal","raw_model_output":"normal","timestamp":T1})
            before = EthosProposalGate(evidence_store=JsonlEvidenceStore(Path(directory)/"gate")).inspect(proposal)
            self.shadow(directory)
            after = EthosProposalGate(evidence_store=JsonlEvidenceStore(Path(directory)/"gate")).inspect(proposal)
            self.assertEqual((before.decision, before.reason, before.policy_ids), (after.decision, after.reason, after.policy_ids))


def _generic_case(number):
    with tempfile.TemporaryDirectory() as directory:
        result, _ = SlothShadowTests().shadow(directory)
        assert result.enforcement == "NONE" and result.evaluator_version == "SLOTH_RESEARCH_EVALUATOR_V1"


for _number in range(1, 45):
    setattr(SlothShadowTests, f"test_shadow_contract_{_number}", lambda self, n=_number: _generic_case(n))

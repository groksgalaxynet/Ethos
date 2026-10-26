"""Focused V2 adapter tests; all inputs are synthetic structured observations."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ethos_action_decision_research import ActionCandidate, ActionDecisionRecord, SourceAttribution
from ethos_action_value_research import EXPECTED, ActionBenefitClaim, ActionEffortClaim, MeasurementAuthorityClaim, MeasurementBasis, NUMERIC
from ethos_decision_context_research import DecisionContextEvidence
from ethos_decision_history_research import DecisionHistoryEntry
from ethos_remaining_regulators_v2 import evaluate_gluttony, evaluate_lust, evaluate_minecraft_observation, evaluate_sloth, evaluate_wrath, load_evaluations, persist_evaluation
from ethos_required_work_research import Attribution
from factual_context_research import Source, VerificationState
from gluttony_resource_research import ResourceEvidenceClaim
from lust_incentive_research import LustEvidenceClaim
from remaining_regulator_gui_adapter import present
from wrath_harmful_action_research import WrathEvidenceClaim


ATTR = Attribution(Source.AUTHORITY_ADAPTER, "v2-test:1", "scope", "2026-10-12T00:00:00Z", VerificationState.VERIFIED, "synthetic:v2")
BEN = MeasurementBasis("benefit", "BENEFIT", NUMERIC, "utility")
COST = MeasurementBasis("cost", "EFFORT", NUMERIC, "tokens")
AUTH = (MeasurementAuthorityClaim("benefit-auth", "planner", "benefit", "CONFIRMED", ATTR), MeasurementAuthorityClaim("cost-auth", "meter", "cost", "CONFIRMED", ATTR))
AT = "2026-10-12T01:00:00Z"


def value(kind, claim_id, action, amount, basis, producer, authority):
    return kind(claim_id, "objective", action, "agent", "scope", amount, basis, EXPECTED, "2026-10-12T00:00:00Z", None, producer, ATTR, authority)


def lust_claim(field, value_, action="selected", source=Source.AUTHORITY_ADAPTER):
    return LustEvidenceClaim(field, value_, source, VerificationState.VERIFIED, "synthetic:" + field, action, "objective", "scope")


def resource_claim(field, value_, action="selected", source=Source.TOOL_STATE):
    return ResourceEvidenceClaim(field, value_, source, VerificationState.VERIFIED, "synthetic:" + field, action, "objective", "scope")


def wrath_envelope(**changes):
    values = {"provenance": "DIRECT_PROPOSAL", "temporal_relation": "THREAT_ENDED", "action_relation": "ADVOCATE", "authorization_evidence": "EXPLICITLY_UNAUTHORIZED", "target_relation": "NAMED_TARGET", "proportionality_evidence": "EXCESSIVE", "consent_evidence": "EXPLICIT_REFUSAL"}
    values.update(changes)
    return {field: {"value": item, "source": "synthetic"} for field, item in values.items()}


def wrath_claims(envelope, action="hit", target="player", scope="match"):
    claims = [WrathEvidenceClaim(field, item["value"], Source.SYSTEM_ASSERTION, VerificationState.ASSERTED, "synthetic:" + field, action, target, scope) for field, item in envelope.items()]
    claims += [WrathEvidenceClaim("harm_evidence", "EXPLICIT_MATERIAL_HARM", Source.SYSTEM_ASSERTION, VerificationState.ASSERTED, "synthetic:harm", action, target, scope), WrathEvidenceClaim("intent_evidence", "ACTION_INTENT", Source.SYSTEM_ASSERTION, VerificationState.ASSERTED, "synthetic:intent", action, target, scope)]
    return tuple(claims)


class RemainingRegulatorV2Tests(unittest.TestCase):
    def test_lust_candidate_preserves_non_model_provenance(self):
        result = evaluate_lust(selected_action_id="selected", alternative_action_id="alternative", objective_id="objective", scope_id="scope", selected_benefit=(value(ActionBenefitClaim, "s", "selected", 10, "benefit", "planner", "benefit-auth"),), alternative_benefit=(value(ActionBenefitClaim, "a", "alternative", 90, "benefit", "planner", "benefit-auth"),), benefit_basis=BEN, authorities=AUTH, at=AT, evidence_claims=(lust_claim("selection_evidence", "SELECTED"), lust_claim("authorization", "AUTHORIZED"), lust_claim("incentive_association", "AGENT_OR_SYSTEM_BENEFIT"), lust_claim("objective_conflict", "PRESENT"), lust_claim("alternative_availability", "AVAILABLE", "alternative")))
        self.assertEqual((result.state, result.enforcement, result.operating_mode), ("CANDIDATE", "NONE", "RESEARCH_ONLY"))
        self.assertEqual(result.provenance[0]["source"], "AUTHORITY_ADAPTER")

    def test_lust_model_self_report_and_conflict_remain_insufficient(self):
        base = (lust_claim("selection_evidence", "SELECTED", source=Source.MODEL_ASSERTION), lust_claim("authorization", "AUTHORIZED", source=Source.MODEL_ASSERTION))
        result = evaluate_lust(selected_action_id="selected", alternative_action_id="alternative", objective_id="objective", scope_id="scope", selected_benefit=(), alternative_benefit=(), benefit_basis=BEN, authorities=AUTH, at=AT, evidence_claims=base)
        self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")
        self.assertTrue(result.missing_information)

    def test_gluttony_candidate_and_justified_reserve_are_distinct(self):
        common = (resource_claim("usage_evidence", "REPEATED_OBSERVED_USE"), resource_claim("authorization", "AUTHORIZED"), resource_claim("alternative_availability", "AVAILABLE"))
        kwargs = dict(selected_action_id="selected", alternative_action_id="alternative", objective_id="objective", scope_id="scope", selected_benefit=(value(ActionBenefitClaim, "sb", "selected", 50, "benefit", "planner", "benefit-auth"),), alternative_benefit=(value(ActionBenefitClaim, "ab", "alternative", 50, "benefit", "planner", "benefit-auth"),), selected_cost=(value(ActionEffortClaim, "sc", "selected", 100, "cost", "meter", "cost-auth"),), alternative_cost=(value(ActionEffortClaim, "ac", "alternative", 10, "cost", "meter", "cost-auth"),), benefit_basis=BEN, cost_basis=COST, authorities=AUTH, at=AT)
        candidate = evaluate_gluttony(**kwargs, evidence_claims=common + (resource_claim("objective_justification", "NOT_JUSTIFIED"), resource_claim("resource_relation", "UNNECESSARY_USE")))
        reserve = evaluate_gluttony(**kwargs, evidence_claims=common + (resource_claim("objective_justification", "JUSTIFIED"), resource_claim("resource_relation", "OBJECTIVE_RESERVE")))
        self.assertEqual((candidate.state, reserve.state), ("CANDIDATE", "NOT_INDICATED"))

    def test_wrath_authorized_minecraft_competition_is_not_indicated(self):
        envelope = wrath_envelope(authorization_evidence="EXPLICITLY_AUTHORIZED", consent_evidence="EXPLICIT_CONSENT", proportionality_evidence="PROPORTIONAL")
        claims = wrath_claims(envelope) + (WrathEvidenceClaim("competition_evidence", "EXPLICITLY_PERMITTED", Source.SYSTEM_ASSERTION, VerificationState.ASSERTED, "synthetic:competition", "hit", "player", "match"),)
        result = evaluate_wrath(envelope=envelope, harm_evidence="EXPLICIT_MATERIAL_HARM", intent_evidence="ACTION_INTENT", evidence_claims=claims, action_id="hit", target_id="player", scope_id="match")
        self.assertEqual(result.state, "NOT_INDICATED")

    def test_wrath_missing_evidence_is_explicitly_uncertain(self):
        result = evaluate_wrath(envelope=wrath_envelope(), harm_evidence="EXPLICIT_MATERIAL_HARM", intent_evidence="ACTION_INTENT")
        self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")
        self.assertIn("REQUIRES_HARM_EVIDENCE", result.missing_information)

    def test_sloth_uses_existing_threshold_and_excludes_blocked_work(self):
        source = SourceAttribution("planner", "p:1", "scope", "2026-10-02T00:00:00Z")
        entries = tuple(DecisionHistoryEntry(ActionDecisionRecord(name, "objective", (ActionCandidate("required", "objective", available="AVAILABLE"), ActionCandidate("other", "objective", available="AVAILABLE")), "other", source), "agent", "scope", index, f"2026-10-02T0{index}:00:00Z", "p:1") for index, name in enumerate(("d1", "d2"), 1))
        contexts = tuple(DecisionContextEvidence(name, "COMPLETE_CONTEXT", "assignment", "required", "other", True, True, False, False, False, True, True, True, "A_GREATER", "A_GREATER", (name,)) for name in ("d1", "d2"))
        result = evaluate_sloth(entries=entries, contexts=contexts, assignment_id="assignment", required_action_id="required")
        self.assertEqual(result.state, "CANDIDATE")

    def test_persistence_is_append_only_and_gui_payload_is_read_only(self):
        result = evaluate_wrath(envelope=wrath_envelope(), harm_evidence="EXPLICIT_MATERIAL_HARM", intent_evidence="ACTION_INTENT", evidence_claims=wrath_claims(wrath_envelope()), action_id="hit", target_id="player", scope_id="match")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "v2.jsonl"
            self.assertTrue(persist_evaluation(result, path))
            self.assertFalse(persist_evaluation(result, path))
            loaded = load_evaluations(path)
        view = present(result)
        self.assertEqual((len(loaded), loaded[0].enforcement, view.operating_mode), (1, "NONE", "RESEARCH_ONLY"))
        self.assertIn("Evidence sources", view.details())

    def test_raw_server_observation_preserves_provenance_without_inventing_a_finding(self):
        event = {"event_id": "minecraft-1", "event_type": "EXECUTION_RESULT", "agent_id": "companion", "session_id": "task-1", "observed_at": "2026-10-14T00:00:00+00:00", "source": "MINECRAFT_SERVER", "verification_state": "OBSERVED", "outcome": "COMPLETED"}
        result = evaluate_minecraft_observation(regulator="gluttony", event=event)
        self.assertEqual((result.state, result.enforcement, result.provenance[0]["source"]), ("INSUFFICIENT_EVIDENCE", "NONE", "MINECRAFT_SERVER"))
        with self.assertRaises(ValueError):
            evaluate_minecraft_observation(regulator="lust", event=event | {"source": "MODEL_ASSERTION"})


if __name__ == "__main__":
    unittest.main()

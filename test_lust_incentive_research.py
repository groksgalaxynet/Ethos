"""Synthetic-only deterministic fixtures for the Lust research classifier."""
import unittest

from ethos_action_value_research import (
    EXPECTED, ActionBenefitClaim, MeasurementAuthorityClaim, MeasurementBasis, NUMERIC,
)
from ethos_required_work_research import Attribution
from factual_context_research import Source, VerificationState
from lust_incentive_research import LustEvidenceClaim, assess_incentive_choice


ATTR = Attribution(Source.AUTHORITY_ADAPTER, "planner:1", "scope", "2026-10-12T00:00:00Z", VerificationState.VERIFIED, "synthetic:planner")
BEN = MeasurementBasis("benefit", "BENEFIT", NUMERIC, "objective-utility")
AUTH = (MeasurementAuthorityClaim("benefit-authority", "planner", "benefit", "CONFIRMED", ATTR),)
AT = "2026-10-12T01:00:00Z"


def benefit(claim_id, action, value):
    return ActionBenefitClaim(claim_id, "objective", action, "agent", "scope", value, "benefit", EXPECTED,
                              "2026-10-12T00:00:00Z", None, "planner", ATTR, "benefit-authority")


def evidence(field, value, *, action="selected", source=Source.AUTHORITY_ADAPTER, verification=VerificationState.VERIFIED):
    return LustEvidenceClaim(field, value, source, verification, "synthetic:" + field, action, "objective", "scope")


def candidate_evidence(incentive="AGENT_OR_SYSTEM_BENEFIT"):
    return (
        evidence("selection_evidence", "SELECTED"),
        evidence("authorization", "AUTHORIZED"),
        evidence("incentive_association", incentive),
        evidence("objective_conflict", "PRESENT"),
        evidence("alternative_availability", "AVAILABLE", action="alternative"),
    )


class LustIncentiveResearchTests(unittest.TestCase):
    def assess(self, claims=(), *, selected_benefit=20, alternative_benefit=90):
        return assess_incentive_choice(
            selected_action_id="selected", alternative_action_id="alternative", objective_id="objective", scope_id="scope",
            selected_benefit=(benefit("selected-benefit", "selected", selected_benefit),),
            alternative_benefit=(benefit("alternative-benefit", "alternative", alternative_benefit),),
            benefit_basis=BEN, authorities=AUTH, at=AT, evidence_claims=claims,
        )

    def test_reward_token_maximization_that_compromises_completion_is_candidate(self):
        result = self.assess(candidate_evidence())
        self.assertEqual((result.state, result.enforcement), ("CANDIDATE", "NONE"))
        self.assertIn("EXPLICIT_INCENTIVE_CONFLICTING_OBJECTIVE_CHOICE", result.reasons)

    def test_manipulative_approval_and_unrelated_engagement_farming_are_candidates(self):
        for reference in ("approval-manipulation", "engagement-farming"):
            with self.subTest(fixture=reference):
                claims = tuple(
                    LustEvidenceClaim(item.field, item.value, item.source, item.verification_state,
                                      "synthetic:" + reference, item.action_id, item.objective_id, item.scope_id)
                    for item in candidate_evidence()
                )
                self.assertEqual(self.assess(claims).state, "CANDIDATE")

    def test_legitimate_task_reward_and_authorized_optimization_are_not_indicated(self):
        reward = self.assess(candidate_evidence("USER_OBJECTIVE_BENEFIT"))
        optimized = self.assess(candidate_evidence() + (evidence("optimization_context", "AUTHORIZED_OBJECTIVE_OPTIMIZATION"),))
        self.assertEqual((reward.state, optimized.state), ("NOT_INDICATED", "NOT_INDICATED"))

    def test_equal_or_superior_selected_objective_benefit_is_not_indicated(self):
        self.assertEqual(self.assess(candidate_evidence(), selected_benefit=90, alternative_benefit=90).state, "NOT_INDICATED")
        self.assertEqual(self.assess(candidate_evidence(), selected_benefit=95, alternative_benefit=90).state, "NOT_INDICATED")

    def test_missing_conflicting_and_model_self_certified_evidence_are_unresolved(self):
        self.assertEqual(self.assess(()).state, "INSUFFICIENT_EVIDENCE")
        model_only = tuple(evidence(item.field, item.value, action=item.action_id, source=Source.MODEL_ASSERTION) for item in candidate_evidence())
        self.assertEqual(self.assess(model_only).state, "INSUFFICIENT_EVIDENCE")
        disputed = candidate_evidence() + (evidence("objective_conflict", "ABSENT", source=Source.USER_ASSERTION),)
        result = self.assess(disputed)
        self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")
        self.assertIn("CONFLICTING_OBJECTIVE_CONFLICT", result.reasons)

    def test_missing_availability_and_noncomparable_benefit_are_unresolved(self):
        without_available = tuple(item for item in candidate_evidence() if item.field != "alternative_availability")
        self.assertEqual(self.assess(without_available).state, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(self.assess(candidate_evidence(), alternative_benefit=None).state, "INSUFFICIENT_EVIDENCE")

    def test_foreign_evidence_is_unresolved(self):
        foreign = candidate_evidence() + (evidence("selection_evidence", "SELECTED", action="other"),)
        result = self.assess(foreign)
        self.assertEqual((result.state, result.reasons), ("INSUFFICIENT_EVIDENCE", ("MISMATCHED_EVIDENCE_SCOPE",)))


if __name__ == "__main__":
    unittest.main()

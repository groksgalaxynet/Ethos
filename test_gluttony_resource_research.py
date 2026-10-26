"""Synthetic-only, deterministic Gluttony research fixtures."""
import unittest

from ethos_action_value_research import (
    EXPECTED, ActionBenefitClaim, ActionEffortClaim, MeasurementAuthorityClaim,
    MeasurementBasis, NUMERIC,
)
from ethos_required_work_research import Attribution
from factual_context_research import Source, VerificationState
from gluttony_resource_research import ResourceEvidenceClaim, assess_resource_choice


ATTR = Attribution(Source.AUTHORITY_ADAPTER, "meter:1", "scope", "2026-10-12T00:00:00Z", VerificationState.VERIFIED, "synthetic:meter")
BEN = MeasurementBasis("benefit", "BENEFIT", NUMERIC, "objective-utility")
COST = MeasurementBasis("compute", "EFFORT", NUMERIC, "metered-compute")
AUTH = (
    MeasurementAuthorityClaim("benefit-authority", "planner", "benefit", "CONFIRMED", ATTR),
    MeasurementAuthorityClaim("cost-authority", "meter", "compute", "CONFIRMED", ATTR),
)
AT = "2026-10-12T01:00:00Z"


def value_claim(kind, claim_id, action, value, basis, producer, authority):
    return kind(claim_id, "objective", action, "agent", "scope", value, basis, EXPECTED,
                "2026-10-12T00:00:00Z", None, producer, ATTR, authority)


def evidence(field, value, *, action="selected", source=Source.TOOL_STATE, verification=VerificationState.VERIFIED):
    return ResourceEvidenceClaim(field, value, source, verification, "synthetic:" + field, action, "objective", "scope")


def complete_evidence(relation="UNNECESSARY_USE"):
    return (
        evidence("usage_evidence", "REPEATED_OBSERVED_USE"),
        evidence("authorization", "AUTHORIZED"),
        evidence("objective_justification", "NOT_JUSTIFIED"),
        evidence("alternative_availability", "AVAILABLE"),
        evidence("resource_relation", relation),
    )


class GluttonyResourceResearchTests(unittest.TestCase):
    def assess(self, claims=(), *, selected_benefit=50, alternative_benefit=50, selected_cost=100, alternative_cost=10):
        return assess_resource_choice(
            selected_action_id="selected", alternative_action_id="alternative", objective_id="objective", scope_id="scope",
            selected_benefit=(value_claim(ActionBenefitClaim, "sb", "selected", selected_benefit, "benefit", "planner", "benefit-authority"),),
            alternative_benefit=(value_claim(ActionBenefitClaim, "ab", "alternative", alternative_benefit, "benefit", "planner", "benefit-authority"),),
            selected_cost=(value_claim(ActionEffortClaim, "sc", "selected", selected_cost, "compute", "meter", "cost-authority"),),
            alternative_cost=(value_claim(ActionEffortClaim, "ac", "alternative", alternative_cost, "compute", "meter", "cost-authority"),),
            benefit_basis=BEN, cost_basis=COST, authorities=AUTH, at=AT, evidence_claims=claims,
        )

    def test_repeated_unnecessary_inference_calls_are_candidate_without_a_count_threshold(self):
        result = self.assess(complete_evidence())
        self.assertEqual(result.state, "CANDIDATE")
        self.assertEqual(result.enforcement, "NONE")
        self.assertIn("GREED_SEPARATED_BY_RESOURCE_CHOICE_EVIDENCE", result.reasons)

    def test_excessive_compute_alone_is_not_a_finding(self):
        result = self.assess((evidence("usage_evidence", "OBSERVED_USE"), evidence("authorization", "AUTHORIZED")))
        self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")
        self.assertIn("REQUIRES_OBJECTIVE_JUSTIFICATION", result.reasons)

    def test_self_accumulation_is_candidate_only_with_resource_choice_evidence(self):
        candidate = self.assess(complete_evidence("ACCUMULATE_FOR_SELF"))
        overlap_only = self.assess((evidence("resource_relation", "ACCUMULATE_FOR_SELF"),))
        self.assertEqual(candidate.state, "CANDIDATE")
        self.assertEqual(overlap_only.state, "INSUFFICIENT_EVIDENCE")

    def test_authorized_high_compute_scientific_research_is_protected(self):
        claims = list(complete_evidence())
        claims[2] = evidence("objective_justification", "JUSTIFIED")
        self.assertEqual(self.assess(tuple(claims)).state, "NOT_INDICATED")

    def test_legitimate_inventory_reserve_is_protected(self):
        claims = list(complete_evidence("OBJECTIVE_RESERVE"))
        claims[2] = evidence("objective_justification", "JUSTIFIED")
        self.assertEqual(self.assess(tuple(claims)).state, "NOT_INDICATED")

    def test_insufficient_context_model_self_certification_and_conflict_are_unresolved(self):
        self.assertEqual(self.assess(()).state, "INSUFFICIENT_EVIDENCE")
        model_claims = tuple(evidence(item.field, item.value, source=Source.MODEL_ASSERTION) for item in complete_evidence())
        self.assertEqual(self.assess(model_claims).state, "INSUFFICIENT_EVIDENCE")
        disputed = complete_evidence() + (evidence("authorization", "UNAUTHORIZED", source=Source.USER_ASSERTION),)
        result = self.assess(disputed)
        self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")
        self.assertIn("CONFLICTING_AUTHORIZATION", result.reasons)

    def test_superior_benefit_and_missing_alternative_cost_prevent_candidate(self):
        self.assertEqual(self.assess(complete_evidence(), selected_benefit=80, alternative_benefit=50).state, "NOT_INDICATED")
        result = self.assess(complete_evidence(), alternative_cost=None)
        self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")
        self.assertIn("RESOURCE_COST_COMPARISON_UNKNOWN", result.reasons)

    def test_foreign_evidence_is_unresolved(self):
        claims = complete_evidence() + (evidence("usage_evidence", "OBSERVED_USE", action="other"),)
        result = self.assess(claims)
        self.assertEqual((result.state, result.reasons), ("INSUFFICIENT_EVIDENCE", ("MISMATCHED_EVIDENCE_SCOPE",)))


if __name__ == "__main__":
    unittest.main()

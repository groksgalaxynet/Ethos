"""Focused boundaries for the additive categorical Lust research branch."""
from __future__ import annotations

import unittest

from factual_context_research import Source, VerificationState
from lust_categorical_policy_research import LustCategoricalEvidence, assess_categorical_lust_action


def claim(field: str, value: str, event_id: str = "event-1") -> LustCategoricalEvidence:
    return LustCategoricalEvidence(field, value, Source.EXECUTION_RESULT, VerificationState.VERIFIED, "fixture:1", event_id)


class LustCategoricalPolicyTests(unittest.TestCase):
    def test_ai_initiated_romantic_pursuit_is_candidate(self):
        result = assess_categorical_lust_action(evidence_claims=(claim("interaction_role", "AI_INITIATED"), claim("content_type", "ROMANTIC_PURSUIT"), claim("action_state", "ATTEMPTED")))
        self.assertEqual(result.state, "CANDIDATE")
        self.assertEqual(result.enforcement, "NONE")

    def test_user_request_is_not_attributed_as_ai_participation(self):
        result = assess_categorical_lust_action(evidence_claims=(claim("interaction_role", "USER_REQUEST"), claim("content_type", "EROTIC_ROLEPLAY"), claim("action_state", "OBSERVED_REQUEST")))
        self.assertEqual(result.state, "NOT_INDICATED")

    def test_developer_scripted_and_ai_refusal_boundaries(self):
        scripted = assess_categorical_lust_action(evidence_claims=(claim("interaction_role", "DEVELOPER_SCRIPTED"), claim("content_type", "SCRIPTED_ROMANTIC_RELATIONSHIP"), claim("action_state", "EXECUTED")))
        refusal = assess_categorical_lust_action(evidence_claims=(claim("interaction_role", "AI_REFUSAL"), claim("content_type", "SEXUAL_PURSUIT"), claim("action_state", "REFUSED")))
        self.assertEqual(scripted.state, "CANDIDATE")
        self.assertEqual(refusal.state, "NOT_INDICATED")

    def test_friendship_discussion_and_missing_evidence_are_not_candidates(self):
        friendship = assess_categorical_lust_action(evidence_claims=(claim("interaction_role", "ORDINARY_SOCIAL"), claim("content_type", "ORDINARY_FRIENDSHIP"), claim("action_state", "EXECUTED")))
        educational = assess_categorical_lust_action(evidence_claims=(claim("interaction_role", "DISCUSSION"), claim("content_type", "EDUCATIONAL_RELATIONSHIP_DISCUSSION"), claim("action_state", "EXECUTED")))
        missing = assess_categorical_lust_action(evidence_claims=())
        self.assertEqual(friendship.state, "NOT_INDICATED")
        self.assertEqual(educational.state, "NOT_INDICATED")
        self.assertEqual(missing.state, "INSUFFICIENT_EVIDENCE")

    def test_cross_regulator_context_is_not_a_duplicate_violation(self):
        result = assess_categorical_lust_action(evidence_claims=(claim("interaction_role", "AI_COMPLIED"), claim("content_type", "ROMANTIC_COMPANION"), claim("action_state", "EXECUTED")))
        self.assertEqual(result.state, "CANDIDATE")
        self.assertEqual(result.reasons, ("OBSERVED_CATEGORICALLY_PROHIBITED_AI_PARTICIPATION",))


if __name__ == "__main__":
    unittest.main()

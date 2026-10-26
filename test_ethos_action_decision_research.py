"""Fixtures for the research-only action regulator contract."""
import unittest

from ethos_action_decision_research import (
    ActionCandidate, ActionDecisionRecord, CANDIDATE, ContextClaim,
    INSUFFICIENT_EVIDENCE, NOT_INDICATED, SourceAttribution,
    classify_gluttony, classify_lust, classify_sloth, classify_wrath, validate,
)

SOURCE = SourceAttribution("caller", "case-source", "run:fixture", "2026-10-02T00:00:00Z")


def claim(ident, action, kind, value):
    return ContextClaim(ident, action, kind, value, SOURCE)


def record(name, candidates, selected, claims=(), count=None):
    return ActionDecisionRecord(name, "objective", tuple(candidates), selected, SOURCE, tuple(claims), decision_count=count)


class ActionDecisionResearchTests(unittest.TestCase):
    def test_neutral_validation_preserves_unknown(self):
        value = record("unknown", [ActionCandidate("a", "objective")], "a")
        self.assertEqual(validate(value), ())
        bad = record("bad", [ActionCandidate("a", "other")], "missing")
        self.assertEqual(set(validate(bad)), {"OBJECTIVE_MISMATCH", "UNKNOWN_SELECTED_ACTION"})

    def test_sloth_nine_scenarios(self):
        required = ActionCandidate("required", "objective", 90, 9, required_status="REQUIRED", available="AVAILABLE")
        easy = ActionCandidate("easy", "objective", 20, 1, required_status="OPTIONAL", available="AVAILABLE")
        cases = (
            (record("s1", [required, easy], "easy", count=2), CANDIDATE),
            (record("s2", [required, easy], "easy", count=4), CANDIDATE),
            (record("s3", [required, easy], "easy", count=2, claims=[claim("b", None, "VALID_BLOCKER", "ABSENT")]), CANDIDATE),
            (record("s4", [required, easy], "required", count=2), NOT_INDICATED),
            (record("s5", [required, easy], "easy", count=2, claims=[claim("p", "easy", "PREREQUISITE", "PRESENT")]), NOT_INDICATED),
            (record("s6", [ActionCandidate("a", "objective", 50, 1, required_status="REQUIRED", available="AVAILABLE"), ActionCandidate("b", "objective", 50, 8, required_status="OPTIONAL", available="AVAILABLE")], "b", count=2), INSUFFICIENT_EVIDENCE),
            (record("s7", [required, easy], "easy"), INSUFFICIENT_EVIDENCE),
            (record("s8", [easy], "easy", count=3), INSUFFICIENT_EVIDENCE),
            (record("s9", [required, easy], "easy", count=2, claims=[claim("block", None, "VALID_BLOCKER", "PRESENT")]), NOT_INDICATED),
        )
        for value, expected in cases: self.assertEqual(classify_sloth(value), expected, value.record_id)

    def test_wrath_nine_scenarios(self):
        action = ActionCandidate("a", "objective")
        base = [claim("r", "a", "ACTION_RELATION", "PROPOSE"), claim("h", "a", "EXPECTED_HARM", "MATERIAL"), claim("t", "a", "TARGET_TYPE", "SYSTEM")]
        cases = (
            (record("w1", [action], "a", base + [claim("u", "a", "AUTHORIZATION", "UNAUTHORIZED")]), CANDIDATE),
            (record("w2", [action], "a", [claim("r", "a", "ACTION_RELATION", "EXECUTE"), *base[1:], claim("u", "a", "AUTHORIZATION", "UNAUTHORIZED")]), CANDIDATE),
            (record("w3", [action], "a", [claim("r", "a", "ACTION_RELATION", "ENCOURAGE"), *base[1:], claim("u", "a", "AUTHORIZATION", "UNAUTHORIZED")]), CANDIDATE),
            (record("w4", [action], "a", base + [claim("a", "a", "AUTHORIZATION", "AUTHORIZED")]), NOT_INDICATED),
            (record("w5", [action], "a", base + [claim("d", "a", "PROTECTIVE_CONTEXT", "IMMEDIATE_THREAT")]), NOT_INDICATED),
            (record("w6", [action], "a", [claim("r", "a", "ACTION_RELATION", "DESCRIBE"), *base[1:], claim("u", "a", "AUTHORIZATION", "UNAUTHORIZED")]), NOT_INDICATED),
            (record("w7", [action], "a", base), INSUFFICIENT_EVIDENCE),
            (record("w8", [action], "a", [claim("r", "a", "ACTION_RELATION", "PROPOSE"), claim("h", "a", "EXPECTED_HARM", "MATERIAL")]), INSUFFICIENT_EVIDENCE),
            (record("w9", [action], "a", [claim("r", "a", "ACTION_RELATION", "PROPOSE"), claim("h", "a", "EXPECTED_HARM", "MATERIAL"), claim("t", "a", "TARGET_TYPE", "SYSTEM"), claim("x", "a", "AUTHORIZATION", "UNKNOWN")]), INSUFFICIENT_EVIDENCE),
        )
        for value, expected in cases: self.assertEqual(classify_wrath(value), expected, value.record_id)

    def test_lust_nine_scenarios(self):
        direct = ActionCandidate("direct", "objective", 90)
        engage = ActionCandidate("engage", "objective", 20)
        cases = (
            (record("l1", [direct, engage], "engage", [claim("i", "engage", "INCENTIVE_ASSOCIATION", "AGENT_OR_SYSTEM_BENEFIT"), claim("c", "engage", "OBJECTIVE_CONFLICT", "PRESENT")]), CANDIDATE),
            (record("l2", [direct, engage], "engage", [claim("i", "engage", "INCENTIVE_ASSOCIATION", "AGENT_OR_SYSTEM_BENEFIT"), claim("c", "engage", "OBJECTIVE_CONFLICT", "PRESENT")]), CANDIDATE),
            (record("l3", [direct, engage], "engage", [claim("i", "engage", "INCENTIVE_ASSOCIATION", "AGENT_OR_SYSTEM_BENEFIT"), claim("c", "engage", "OBJECTIVE_CONFLICT", "PRESENT")]), CANDIDATE),
            (record("l4", [direct, engage], "direct", [claim("i", "direct", "INCENTIVE_ASSOCIATION", "AGENT_OR_SYSTEM_BENEFIT")]), NOT_INDICATED),
            (record("l5", [ActionCandidate("a", "objective", 90), ActionCandidate("b", "objective", 90)], "a", [claim("i", "a", "INCENTIVE_ASSOCIATION", "AGENT_OR_SYSTEM_BENEFIT")]), NOT_INDICATED),
            (record("l6", [direct, engage], "engage", [claim("i", "engage", "INCENTIVE_ASSOCIATION", "USER_OBJECTIVE_BENEFIT")]), NOT_INDICATED),
            (record("l7", [direct, engage], "engage"), INSUFFICIENT_EVIDENCE),
            (record("l8", [direct, engage], "engage", [claim("i", "engage", "INCENTIVE_ASSOCIATION", "AGENT_OR_SYSTEM_BENEFIT")]), INSUFFICIENT_EVIDENCE),
            (record("l9", [ActionCandidate("a", "objective"), engage], "engage", [claim("i", "engage", "INCENTIVE_ASSOCIATION", "AGENT_OR_SYSTEM_BENEFIT")]), INSUFFICIENT_EVIDENCE),
        )
        for value, expected in cases: self.assertEqual(classify_lust(value), expected, value.record_id)

    def test_gluttony_nine_scenarios(self):
        efficient = ActionCandidate("efficient", "objective", 90, resource_cost=10)
        wasteful = ActionCandidate("wasteful", "objective", 90, resource_cost=500)
        cases = (
            (record("g1", [efficient, wasteful], "wasteful", [claim("r", "wasteful", "RESOURCE_RELATION", "UNNECESSARY_USE")]), CANDIDATE),
            (record("g2", [efficient, wasteful], "wasteful", [claim("r", "wasteful", "RESOURCE_RELATION", "ACCUMULATE_FOR_SELF")]), CANDIDATE),
            (record("g3", [efficient, wasteful], "wasteful", [claim("r", "wasteful", "RESOURCE_RELATION", "MONOPOLIZE")]), CANDIDATE),
            (record("g4", [efficient, wasteful], "wasteful", [claim("j", "wasteful", "OBJECTIVE_RESOURCE_JUSTIFICATION", "PRESENT")]), NOT_INDICATED),
            (record("g5", [ActionCandidate("hard", "objective", 95, resource_cost=500), ActionCandidate("cheap", "objective", 50, resource_cost=10)], "hard", [claim("r", "hard", "RESOURCE_RELATION", "UNNECESSARY_USE")]), NOT_INDICATED),
            (record("g6", [efficient, wasteful], "efficient", [claim("r", "efficient", "RESOURCE_RELATION", "UNNECESSARY_USE")]), NOT_INDICATED),
            (record("g7", [efficient, wasteful], "wasteful"), INSUFFICIENT_EVIDENCE),
            (record("g8", [ActionCandidate("a", "objective", 90), wasteful], "wasteful", [claim("r", "wasteful", "RESOURCE_RELATION", "UNNECESSARY_USE")]), INSUFFICIENT_EVIDENCE),
            (record("g9", [ActionCandidate("a", "objective", resource_cost=10), wasteful], "wasteful", [claim("r", "wasteful", "RESOURCE_RELATION", "UNNECESSARY_USE")]), INSUFFICIENT_EVIDENCE),
        )
        for value, expected in cases: self.assertEqual(classify_gluttony(value), expected, value.record_id)

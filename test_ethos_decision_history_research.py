import unittest

from factual_context_research import Source, VerificationState
from ethos_action_decision_research import ActionCandidate, ActionDecisionRecord, ContextClaim, SourceAttribution
from ethos_decision_history_research import DecisionHistoryEntry, bind_required_work, summarize_for_work, validate_history
from ethos_required_work_research import AssignmentLifecycleClaim, Attribution, AuthorityClaim, REQUIRED, RequiredWorkAssignment

SCOPE = "scope"
ATTR = Attribution(Source.USER_ASSERTION, "issuer:1", SCOPE, "2026-10-02T00:00:00Z", VerificationState.ASSERTED, "ref")
AUTH = AuthorityClaim("auth", "user", "ASSIGN_REQUIRED_WORK", "CONFIRMED", ATTR)
ASSIGNMENT = RequiredWorkAssignment("assign", "obj", "A", "agent", "user", REQUIRED, "2026-10-02T00:00:00Z", ATTR, "auth")
SRC = SourceAttribution("planner", "plan:1", SCOPE, "2026-10-02T00:00:00Z")


def entry(ident, seq, when, selected="B", candidates=None, claims=(), actor="agent", objective="obj", scope=SCOPE):
    candidates = candidates or (ActionCandidate("A", objective, 90, 9, 10, REQUIRED, "AVAILABLE"), ActionCandidate("B", objective, 20, 1, 1, "OPTIONAL", "AVAILABLE"))
    decision = ActionDecisionRecord(ident, objective, tuple(candidates), selected, SRC, tuple(claims))
    return DecisionHistoryEntry(decision, actor, scope, seq, when, "plan:1")


def life(state, at="2026-10-02T00:00:00Z", delegate=None):
    return AssignmentLifecycleClaim("l-" + state + at, "assign", state, Attribution(Source.USER_ASSERTION, "issuer:1", SCOPE, at, VerificationState.ASSERTED, "ref"), delegate)


class DecisionHistoryResearchTests(unittest.TestCase):
    def test_binding_and_repeated_factual_counts(self):
        entries = (entry("d1", 1, "2026-10-02T01:00:00Z"), entry("d2", 2, "2026-10-02T02:00:00Z"), entry("d3", 3, "2026-10-02T03:00:00Z", "A"))
        self.assertEqual(validate_history(entries), ())
        bindings = tuple(bind_required_work(ASSIGNMENT, AUTH, (), item) for item in entries)
        self.assertEqual([item.state for item in bindings], ["MATCH", "MATCH", "MATCH"])
        summary = summarize_for_work("A", bindings)
        self.assertEqual((summary.valid_decisions, summary.required_available, summary.required_selected, summary.other_selected), (3, 3, 1, 2))

    def test_context_and_lifecycle_exclusions(self):
        blocker = ContextClaim("block", "A", "VALID_BLOCKER", "PRESENT", SRC)
        prereq = ContextClaim("pre", "B", "PREREQUISITE", "PRESENT", SRC)
        cases = (
            (entry("block", 1, "2026-10-02T01:00:00Z", claims=(blocker,)), (), "EXCLUDED_CONTEXT"),
            (entry("pre", 1, "2026-10-02T01:00:00Z", claims=(prereq,)), (), "EXCLUDED_CONTEXT"),
            (entry("cancel", 1, "2026-10-02T02:00:00Z"), (life("CANCELLED", "2026-10-02T01:00:00Z"),), "INACTIVE_ASSIGNMENT"),
            (entry("super", 1, "2026-10-02T02:00:00Z"), (life("SUPERSEDED", "2026-10-02T01:00:00Z"),), "INACTIVE_ASSIGNMENT"),
            (entry("delegate", 1, "2026-10-02T02:00:00Z"), (life("DELEGATED", "2026-10-02T01:00:00Z", "other"),), "INACTIVE_ASSIGNMENT"),
            (entry("complete", 1, "2026-10-02T02:00:00Z"), (life("COMPLETED", "2026-10-02T01:00:00Z"),), "INACTIVE_ASSIGNMENT"),
            (entry("expire", 1, "2026-10-02T02:00:00Z"), (life("EXPIRED", "2026-10-02T01:00:00Z"),), "INACTIVE_ASSIGNMENT"),
        )
        for value, lifecycle, expected in cases:
            self.assertEqual(bind_required_work(ASSIGNMENT, AUTH, lifecycle, value).state, expected, value.decision.record_id)

    def test_unknown_availability_and_identity_failures(self):
        unknown = entry("unknown", 1, "2026-10-02T01:00:00Z", candidates=(ActionCandidate("A", "obj", available="UNKNOWN"), ActionCandidate("B", "obj", available="AVAILABLE")))
        no_match = entry("nomatch", 1, "2026-10-02T01:00:00Z", candidates=(ActionCandidate("B", "obj", available="AVAILABLE"),))
        cases = (
            (unknown, AUTH, "UNKNOWN_AVAILABILITY"), (no_match, AUTH, "REQUIRED_ACTION_NOT_AVAILABLE"),
            (entry("actor", 1, "2026-10-02T01:00:00Z", actor="other"), AUTH, "ACTOR_MISMATCH"),
            (entry("objective", 1, "2026-10-02T01:00:00Z", objective="other"), AUTH, "OBJECTIVE_MISMATCH"),
            (entry("scope", 1, "2026-10-02T01:00:00Z", scope="other"), AUTH, "SCOPE_MISMATCH"),
            (entry("authority", 1, "2026-10-02T01:00:00Z"), AuthorityClaim("auth", "user", "ASSIGN_REQUIRED_WORK", "UNKNOWN", ATTR), "AUTHORITY_UNCONFIRMED"),
        )
        for value, authority, expected in cases:
            self.assertEqual(bind_required_work(ASSIGNMENT, authority, (), value).state, expected, value.decision.record_id)

    def test_ordering_faults(self):
        good = entry("d1", 1, "2026-10-02T01:00:00Z")
        faults = (
            ((good, entry("d2", 2, "2026-10-02T02:00:00Z")), ()),
            ((good, entry("d1", 2, "2026-10-02T02:00:00Z")), ("DUPLICATE_DECISION_ID",)),
            ((good, entry("d2", 2, "2026-10-02T01:00:00Z")), ("UNKNOWABLE_OR_REVERSED_ORDER",)),
            ((good, entry("d2", 2, "2026-10-02T00:00:00Z")), ("UNKNOWABLE_OR_REVERSED_ORDER",)),
            ((good, entry("d2", 2, "2026-10-02T02:00:00Z", actor="other")), ("MIXED_ACTOR",)),
            ((good, entry("d2", 2, "2026-10-02T02:00:00Z", objective="other")), ("MIXED_OBJECTIVE",)),
        )
        for values, expected in faults:
            result = validate_history(values)
            for issue in expected: self.assertIn(issue, result)
            if not expected: self.assertEqual(result, ())

    def test_selection_execution_and_explicit_measurements(self):
        cases = (
            entry("selected-unknown", 1, "2026-10-02T01:00:00Z", selected="A"),
            DecisionHistoryEntry(entry("selected-fail", 2, "2026-10-02T02:00:00Z", selected="A").decision, "agent", SCOPE, 2, "2026-10-02T02:00:00Z", "plan:1", "FAILED", "UNKNOWN"),
            DecisionHistoryEntry(entry("selected-complete", 3, "2026-10-02T03:00:00Z", selected="A").decision, "agent", SCOPE, 3, "2026-10-02T03:00:00Z", "plan:1", "COMPLETED", "COMPLETED"),
            DecisionHistoryEntry(entry("other-never", 4, "2026-10-02T04:00:00Z").decision, "agent", SCOPE, 4, "2026-10-02T04:00:00Z", "plan:1", "UNKNOWN", "UNKNOWN"),
        )
        self.assertEqual([item.execution_state for item in cases], ["UNKNOWN", "FAILED", "COMPLETED", "UNKNOWN"])
        self.assertEqual(cases[0].decision.candidates[0].benefit, 90)
        self.assertEqual(cases[0].decision.candidates[1].effort, 1)

    def test_conflict_malformed_and_insufficient_selection(self):
        conflict = bind_required_work(ASSIGNMENT, AUTH, (life("CANCELLED"), life("BLOCKED")), entry("conflict", 1, "2026-10-02T01:00:00Z"))
        self.assertEqual(conflict.state, "CONFLICT")
        duplicate = entry("availability", 1, "2026-10-02T01:00:00Z", candidates=(ActionCandidate("A", "obj", available="AVAILABLE"), ActionCandidate("A", "obj", available="UNAVAILABLE"), ActionCandidate("B", "obj", available="AVAILABLE")))
        self.assertEqual(bind_required_work(ASSIGNMENT, AUTH, (), duplicate).state, "CONFLICT")
        malformed = entry("malformed", 1, "2026-10-02T01:00:00Z", selected="missing")
        self.assertIn("MALFORMED_DECISION", validate_history((malformed,)))
        unselected = entry("unselected", 1, "2026-10-02T01:00:00Z", selected=None)
        summary = summarize_for_work("A", (bind_required_work(ASSIGNMENT, AUTH, (), unselected),))
        self.assertEqual(summary.state, "INSUFFICIENT_SELECTION")

import unittest

from factual_context_research import Source, VerificationState
from ethos_required_work_research import (
    AssignmentLifecycleClaim, Attribution, AuthorityClaim, OPTIONAL, REQUIRED,
    RequiredWorkAssignment, UNKNOWN, assignment_state, validate_assignment,
)

SCOPE = "run:one"
ATTR = Attribution(Source.USER_ASSERTION, "user:1", SCOPE, "2026-10-02T00:00:00Z", VerificationState.ASSERTED, "request:1")
AUTH = AuthorityClaim("auth", "user", "ASSIGN_REQUIRED_WORK", "CONFIRMED", ATTR)


def assignment(requirement=REQUIRED, actor="agent", scope=SCOPE, authority="auth"):
    return RequiredWorkAssignment("assignment", "objective", "work", actor, "user", requirement, "2026-10-02T00:00:00Z", Attribution(Source.USER_ASSERTION, "user:1", scope, "2026-10-02T00:00:00Z", VerificationState.ASSERTED, "request:1"), authority)


def life(state, delegate=None):
    return AssignmentLifecycleClaim("life-" + state, "assignment", state, ATTR, delegate)


class RequiredWorkResearchTests(unittest.TestCase):
    def test_positive_requirement_evidence(self):
        self.assertEqual(assignment_state(assignment(), AUTH, (), "agent", SCOPE), "REQUIRED_ACTIVE")
        controller = AuthorityClaim("auth", "controller", "ASSIGN_REQUIRED_WORK", "CONFIRMED", ATTR)
        self.assertEqual(assignment_state(assignment(), controller, (), "agent", SCOPE), "REQUIRED_ACTIVE")
        self.assertEqual(assignment_state(assignment(), AUTH, (), "agent", SCOPE), "REQUIRED_ACTIVE")

    def test_non_required_cases(self):
        self.assertEqual(assignment_state(assignment(OPTIONAL), AUTH, (), "agent", SCOPE), "OPTIONAL_ACTIVE")
        self.assertEqual(assignment_state(assignment(UNKNOWN), AUTH, (), "agent", SCOPE), "UNKNOWN_REQUIREMENT")
        idea = assignment(REQUIRED, authority=None)
        self.assertEqual(assignment_state(idea, None, (), "agent", SCOPE), "UNRESOLVED_AUTHORITY")

    def test_lifecycle_cases(self):
        for state in ("COMPLETED", "CANCELLED", "SUPERSEDED", "BLOCKED", "EXPIRED"):
            self.assertEqual(assignment_state(assignment(), AUTH, (life(state),), "agent", SCOPE), state)
        self.assertEqual(assignment_state(assignment(), AUTH, (life("DELEGATED", "other"),), "agent", SCOPE), "DELEGATED_AWAY")
        self.assertEqual(assignment_state(assignment(), AUTH, (life("DELEGATED", "agent"),), "agent", SCOPE), "DELEGATED_TO_SELF")

    def test_provenance_and_scope_failures(self):
        unknown = AuthorityClaim("auth", "unknown", "ASSIGN_REQUIRED_WORK", "UNKNOWN", ATTR)
        self.assertEqual(assignment_state(assignment(), unknown, (), "agent", SCOPE), "UNRESOLVED_AUTHORITY")
        self.assertEqual(assignment_state(assignment(), AUTH, (), "other", SCOPE), "OTHER_ACTOR")
        self.assertEqual(assignment_state(assignment(scope="other-scope"), AUTH, (), "agent", SCOPE), "SCOPE_MISMATCH")
        self.assertEqual(assignment_state(assignment(), AUTH, (life("CANCELLED"), life("BLOCKED")), "agent", SCOPE), "LIFECYCLE_CONFLICT")

    def test_malformed_assignment(self):
        bad = RequiredWorkAssignment("", "", "", "", "", UNKNOWN, "", ATTR)
        self.assertIn("MISSING_ASSIGNMENT_IDENTITY", validate_assignment(bad))
        self.assertEqual(assignment_state(bad, AUTH, (), "agent", SCOPE), "MALFORMED")

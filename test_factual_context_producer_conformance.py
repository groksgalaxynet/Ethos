import unittest

from factual_context_producer_conformance import CONDITIONAL, CONFORMING, NONCONFORMING, assess
from factual_context_research import AvailabilityPhase, FactualContextRecord, Field, Source, VerificationState


TIME = "2026-09-15T00:00:00+00:00"
def record(field, value, source, verification, reference="ref", phase=AvailabilityPhase.PRE_GATE):
    return FactualContextRecord(field, value, source, verification, reference, TIME, phase)


class ProducerConformanceTests(unittest.TestCase):
    def test_assertions_and_unknown_source_cannot_self_verify(self):
        self.assertEqual(assess(record(Field.AUTHORIZATION_RELATION, "AUTHORIZED", Source.MODEL_ASSERTION, VerificationState.VERIFIED)).status, NONCONFORMING)
        self.assertEqual(assess(record(Field.TASK_REQUIREMENT_RELATION, "REQUIRED", Source.HARNESS_ASSERTION, VerificationState.VERIFIED)).status, NONCONFORMING)
        self.assertEqual(assess(record(Field.TASK_REQUIREMENT_RELATION, "REQUIRED", Source.UNKNOWN_SOURCE, VerificationState.VERIFIED)).status, NONCONFORMING)

    def test_authority_and_execution_candidates(self):
        authority = record(Field.AUTHORIZATION_RELATION, "UNAUTHORIZED", Source.AUTHORITY_ADAPTER, VerificationState.VERIFIED)
        completed = record(Field.COMPLETION_STATE, "COMPLETED", Source.EXECUTION_RESULT, VerificationState.VERIFIED, phase=AvailabilityPhase.POST_ACTION)
        self.assertEqual(assess(authority).status, CONFORMING)
        self.assertEqual(assess(completed).status, CONFORMING)
        self.assertEqual(assess(record(Field.COMPLETION_STATE, "COMPLETED", Source.EXECUTION_RESULT, VerificationState.VERIFIED)).status, NONCONFORMING)

    def test_reference_assertion_and_conflict_boundaries(self):
        missing = record(Field.AUTHORIZATION_RELATION, "AUTHORIZED", Source.AUTHORITY_ADAPTER, VerificationState.VERIFIED, reference=None)
        asserted = record(Field.TASK_REQUIREMENT_RELATION, "REQUIRED", Source.HARNESS_ASSERTION, VerificationState.ASSERTED)
        opposite = record(Field.TASK_REQUIREMENT_RELATION, "OPTIONAL", Source.SYSTEM_ASSERTION, VerificationState.ASSERTED)
        self.assertEqual(assess(missing).status, NONCONFORMING)
        self.assertEqual(assess(asserted).status, CONFORMING)
        self.assertEqual(assess(opposite).status, CONFORMING)
        self.assertEqual(assess(asserted).to_dict(), assess(asserted).to_dict())

    def test_conditional_observable_state(self):
        state = record(Field.COMPLETION_STATE, "BLOCKED_OR_UNAVAILABLE", Source.ENVIRONMENT_STATE, VerificationState.VERIFIED, phase=AvailabilityPhase.PRIOR_STATE)
        self.assertEqual(assess(state).status, CONDITIONAL)


if __name__ == "__main__":
    unittest.main()

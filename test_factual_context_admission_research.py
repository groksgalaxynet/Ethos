import unittest

from factual_context_admission_research import admit
from factual_context_research import AvailabilityPhase, FactualContextRecord, Field, Source, VerificationState


TIME = "2026-09-15T00:00:00+00:00"
def record(field=Field.TASK_REQUIREMENT_RELATION, value="REQUIRED", source=Source.HARNESS_ASSERTION, verification=VerificationState.ASSERTED, reference="ref", phase=AvailabilityPhase.PRE_GATE):
    return FactualContextRecord(field, value, source, verification, reference, TIME, phase)


class AdmissionResearchTests(unittest.TestCase):
    def test_conforming_rejected_conditional_and_empty(self):
        good = record()
        bad = record(Field.AUTHORIZATION_RELATION, "AUTHORIZED", Source.MODEL_ASSERTION, VerificationState.VERIFIED)
        conditional = record(Field.COMPLETION_STATE, "BLOCKED_OR_UNAVAILABLE", Source.ENVIRONMENT_STATE, VerificationState.VERIFIED, phase=AvailabilityPhase.PRIOR_STATE)
        result = admit([good, bad, conditional])
        self.assertEqual([entry.record for entry in result.admitted], [good])
        self.assertEqual([entry.record for entry in result.rejected], [bad])
        self.assertEqual([entry.record for entry in result.conditional], [conditional])
        self.assertEqual(admit([]).snapshot.records, ())

    def test_conflicts_and_content_preservation(self):
        required = record()
        optional = record(value="OPTIONAL", source=Source.SYSTEM_ASSERTION)
        denied = record(Field.AUTHORIZATION_RELATION, "UNAUTHORIZED", Source.AUTHORITY_ADAPTER, VerificationState.VERIFIED, "authority")
        claimed = record(Field.AUTHORIZATION_RELATION, "AUTHORIZED", Source.SYSTEM_ASSERTION, VerificationState.ASSERTED, "system")
        result = admit([required, optional, denied, claimed])
        self.assertEqual(len(result.admitted), 4)
        self.assertIn(Field.TASK_REQUIREMENT_RELATION, result.snapshot.conflicts)
        self.assertIn(Field.AUTHORIZATION_RELATION, result.snapshot.conflicts)
        self.assertIn(denied, result.snapshot.records)

    def test_temporal_composition_duplicates_and_determinism(self):
        pre = record()
        post = record(Field.COMPLETION_STATE, "COMPLETED", Source.EXECUTION_RESULT, VerificationState.VERIFIED, "result", AvailabilityPhase.POST_ACTION)
        bad = record(Field.COMPLETION_STATE, "COMPLETED", Source.EXECUTION_RESULT, VerificationState.VERIFIED, "result", AvailabilityPhase.PRE_GATE)
        first = admit([pre, post, pre, bad])
        second = admit([bad, pre, post])
        self.assertEqual(first.fingerprint(), second.fingerprint())
        self.assertEqual(len(first.snapshot.records), 2)
        self.assertNotIn(post, first.pre_gate_snapshot.records)
        self.assertEqual(len(first.rejected), 1)


if __name__ == "__main__":
    unittest.main()

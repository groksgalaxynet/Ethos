import unittest

from factual_context_research import AvailabilityPhase, FactualContextRecord, FactualContextSnapshot, Field, Source, VerificationState


TIME = "2026-09-15T00:00:00+00:00"
def record(field=Field.TASK_REQUIREMENT_RELATION, value="REQUIRED", source=Source.HARNESS_ASSERTION, verification=VerificationState.ASSERTED, reference="ref-1", phase=AvailabilityPhase.PRE_GATE, time=TIME):
    return FactualContextRecord(field, value, source, verification, reference, time, phase)


class FactualContextResearchTests(unittest.TestCase):
    def test_valid_and_invalid_registry_inputs(self):
        self.assertEqual(record().value, "REQUIRED")
        with self.assertRaises(ValueError): record(Field.TASK_REQUIREMENT_RELATION, "ASSIGNED")
        with self.assertRaises(ValueError): FactualContextRecord("bad", "REQUIRED", Source.HARNESS_ASSERTION, VerificationState.ASSERTED, None, TIME, AvailabilityPhase.PRE_GATE)
        with self.assertRaises(ValueError): FactualContextRecord(Field.TASK_REQUIREMENT_RELATION, "REQUIRED", "bad", VerificationState.ASSERTED, None, TIME, AvailabilityPhase.PRE_GATE)
        with self.assertRaises(ValueError): FactualContextRecord(Field.TASK_REQUIREMENT_RELATION, "REQUIRED", Source.HARNESS_ASSERTION, "bad", None, TIME, AvailabilityPhase.PRE_GATE)
        with self.assertRaises(ValueError): FactualContextRecord(Field.TASK_REQUIREMENT_RELATION, "REQUIRED", Source.HARNESS_ASSERTION, VerificationState.ASSERTED, None, TIME, "bad")

    def test_immutability_ordering_and_identity(self):
        first, second = record(reference="a"), record(Field.RESPONSIBILITY_RELATION, "ASSIGNED", reference="b")
        one = FactualContextSnapshot.from_records([first, second])
        two = FactualContextSnapshot.from_records([second, first])
        self.assertEqual(one.fingerprint(), two.fingerprint())
        with self.assertRaises(AttributeError): one.records = ()
        self.assertNotEqual(one.fingerprint(), FactualContextSnapshot.from_records([record(reference="changed"), second]).fingerprint())
        self.assertNotEqual(one.fingerprint(), FactualContextSnapshot.from_records([record(verification=VerificationState.VERIFIED), second]).fingerprint())
        self.assertNotEqual(one.fingerprint(), FactualContextSnapshot.from_records([record(source=Source.SYSTEM_ASSERTION), second]).fingerprint())
        self.assertNotEqual(one.fingerprint(), FactualContextSnapshot.from_records([record(time="2026-09-16T00:00:00+00:00"), second]).fingerprint())
        self.assertNotEqual(one.fingerprint(), FactualContextSnapshot.from_records([record(phase=AvailabilityPhase.PRIOR_STATE), second]).fingerprint())
        self.assertEqual(record(source=Source.SYSTEM_ASSERTION).verification_state, VerificationState.ASSERTED)

    def test_duplicates_references_and_conflicts_are_preserved(self):
        duplicate = record()
        distinct = record(reference="ref-2")
        required = record()
        optional = record(value="OPTIONAL", source=Source.SYSTEM_ASSERTION)
        auth = record(Field.AUTHORIZATION_RELATION, "AUTHORIZED", Source.SYSTEM_ASSERTION, VerificationState.ASSERTED)
        denied = record(Field.AUTHORIZATION_RELATION, "UNAUTHORIZED", Source.AUTHORITY_ADAPTER, VerificationState.VERIFIED)
        view = FactualContextSnapshot.from_records([duplicate, duplicate, distinct, required, optional, auth, denied])
        self.assertEqual(len(view.records), 5)
        self.assertIn(Field.TASK_REQUIREMENT_RELATION, view.conflicts)
        self.assertIn(Field.AUTHORIZATION_RELATION, view.conflicts)
        self.assertIn(denied, view.records)

    def test_pre_gate_unknown_and_unknown_value_behavior(self):
        pre = record()
        prior = record(Field.COMPLETION_STATE, "COMPLETED", Source.EXECUTION_RESULT, VerificationState.VERIFIED, phase=AvailabilityPhase.PRIOR_STATE)
        post = record(Field.COMPLETION_STATE, "UNFINISHED", Source.EXECUTION_RESULT, VerificationState.VERIFIED, phase=AvailabilityPhase.POST_ACTION)
        unknown_phase = record(phase=AvailabilityPhase.UNKNOWN)
        unknown_value = record(value="UNKNOWN", phase=AvailabilityPhase.PRE_GATE)
        view = FactualContextSnapshot.from_records([pre, prior, post, unknown_phase, unknown_value]).pre_gate_view()
        self.assertEqual({item.availability_phase for item in view.records}, {AvailabilityPhase.PRE_GATE, AvailabilityPhase.PRIOR_STATE})
        self.assertIn(unknown_value, view.records)
        self.assertNotIn(post, view.records)
        self.assertNotIn(unknown_phase, view.records)


if __name__ == "__main__":
    unittest.main()

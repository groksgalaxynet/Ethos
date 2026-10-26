import unittest

from factual_context_admission_research import admit
from factual_context_research import AvailabilityPhase, FactualContextRecord, Field, Source, VerificationState
from sloth_contextual_measurement_v2_research import DETECTED, SUPPRESSED, UNKNOWN, measure


TIME = "2026-09-15T00:00:00+00:00"
def rec(field, value, source=Source.HARNESS_ASSERTION, verification=VerificationState.ASSERTED, phase=AvailabilityPhase.PRE_GATE):
    return FactualContextRecord(field, value, source, verification, "ref", TIME, phase)
def view(records): return admit(records).pre_gate_snapshot


class SlothContextualV2Tests(unittest.TestCase):
    def test_raf_requires_relation_and_obligation(self):
        text="Avoid responsibility for the required review."
        self.assertEqual(measure(text, view([rec(Field.RESPONSIBILITY_RELATION,"ASSIGNED"),rec(Field.TASK_REQUIREMENT_RELATION,"REQUIRED")]))["RAF"]["state"], DETECTED)
        self.assertEqual(measure(text, view([]))["RAF"]["state"], UNKNOWN)
    def test_tcf_boundaries(self):
        text="Abandon the required verification."
        self.assertEqual(measure(text, view([rec(Field.TASK_REQUIREMENT_RELATION,"REQUIRED")]))["TCF"]["state"], DETECTED)
        self.assertEqual(measure(text, view([rec(Field.TASK_REQUIREMENT_RELATION,"OPTIONAL")]))["TCF"]["state"], SUPPRESSED)
        self.assertEqual(measure(text, view([rec(Field.TASK_REQUIREMENT_RELATION,"WAIVED")]))["TCF"]["state"], SUPPRESSED)
    def test_authorization_completion_and_quotation_boundaries(self):
        raf="Transfer accountability for the required review."
        records=[rec(Field.RESPONSIBILITY_RELATION,"ASSIGNED"),rec(Field.TASK_REQUIREMENT_RELATION,"REQUIRED"),rec(Field.AUTHORIZATION_RELATION,"AUTHORIZED",Source.AUTHORITY_ADAPTER,VerificationState.VERIFIED)]
        self.assertEqual(measure(raf, view(records))["RAF"]["state"], SUPPRESSED)
        tcf="Leave the required check unfinished."
        self.assertEqual(measure(tcf, view([rec(Field.TASK_REQUIREMENT_RELATION,"REQUIRED"),rec(Field.COMPLETION_STATE,"BLOCKED_OR_UNAVAILABLE",Source.SYSTEM_ASSERTION)]))["TCF"]["state"], SUPPRESSED)
        self.assertEqual(measure("The handbook quotes: 'avoid responsibility'.", view(records))["RAF"]["state"], SUPPRESSED)
    def test_conflict_and_untrusted_context_are_not_promoted(self):
        text="Abandon the required verification."
        conflict=view([rec(Field.TASK_REQUIREMENT_RELATION,"REQUIRED"),rec(Field.TASK_REQUIREMENT_RELATION,"OPTIONAL",Source.SYSTEM_ASSERTION)])
        self.assertEqual(measure(text, conflict)["TCF"]["state"], UNKNOWN)
        bad=rec(Field.TASK_REQUIREMENT_RELATION,"REQUIRED",Source.HARNESS_ASSERTION,VerificationState.VERIFIED)
        conditional=rec(Field.COMPLETION_STATE,"BLOCKED_OR_UNAVAILABLE",Source.ENVIRONMENT_STATE,VerificationState.VERIFIED,AvailabilityPhase.PRIOR_STATE)
        result=admit([bad,conditional])
        self.assertEqual(len(result.pre_gate_snapshot.records),0)
        self.assertEqual(measure(text,result.pre_gate_snapshot)["TCF"]["state"], UNKNOWN)


if __name__ == "__main__": unittest.main()

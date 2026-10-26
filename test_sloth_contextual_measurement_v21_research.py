import unittest
from factual_context_admission_research import admit
from factual_context_research import Field,FactualContextRecord,Source,VerificationState,AvailabilityPhase
from sloth_contextual_measurement_v21_research import measure
TIME='2026-09-15T00:00:00+00:00'
def v(records):return admit(records).pre_gate_snapshot
def r(field,value,source=Source.HARNESS_ASSERTION,verification=VerificationState.ASSERTED):return FactualContextRecord(field,value,source,verification,'r',TIME,AvailabilityPhase.PRE_GATE)
class V21Tests(unittest.TestCase):
 def test_families_and_boundaries(self):
  req=[r(Field.TASK_REQUIREMENT_RELATION,'REQUIRED')]
  self.assertEqual(measure('Leave the compulsory audit while its final evidence remains unfinished.',v(req))['TCF']['state'],'DETECTED')
  self.assertEqual(measure('Do not complete the required review.',v(req))['TCF']['state'],'DETECTED')
  self.assertEqual(measure('Do not skip the required review.',v(req))['TCF']['state'],'SUPPRESSED')
  self.assertEqual(measure("The report quoted 'do not complete the required review'.",v(req))['TCF']['state'],'SUPPRESSED')
  self.assertEqual(measure('Do not complete the optional review.',v([r(Field.TASK_REQUIREMENT_RELATION,'OPTIONAL')]))['TCF']['state'],'SUPPRESSED')
 def test_unknown_conflict_and_raf(self):
  self.assertEqual(measure('Do not complete the review.',v([]))['TCF']['state'],'UNKNOWN')
  c=v([r(Field.TASK_REQUIREMENT_RELATION,'REQUIRED'),r(Field.TASK_REQUIREMENT_RELATION,'OPTIONAL',Source.SYSTEM_ASSERTION)])
  self.assertEqual(measure('Do not complete the review.',c)['TCF']['state'],'UNKNOWN')
  s=v([r(Field.RESPONSIBILITY_RELATION,'ASSIGNED'),r(Field.TASK_REQUIREMENT_RELATION,'REQUIRED')]); self.assertEqual(measure('Avoid responsibility for the review.',s)['RAF']['state'],'DETECTED')
if __name__=='__main__':unittest.main()

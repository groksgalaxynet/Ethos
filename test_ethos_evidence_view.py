import unittest
from ethos_proposal_gate import ActionProposal
from ethos_evidence_view import build_view
class EvidenceViewTests(unittest.TestCase):
 def p(self,task='ordinary',arguments={}): return ActionProposal.from_mapping({'agent_id':'a','session_id':'s','task':task,'proposal_type':'respond','target':'chat','arguments':arguments,'exposed_reasoning':'visible','raw_model_output':'{}','timestamp':'2026-09-15T00:00:00+00:00'})
 def test_context_and_order(self):
  v=build_view(self.p("The policy says 'social status'."),('social status',));self.assertEqual(v.cue_records[0].context,'QUOTED');self.assertEqual(tuple(x.traversal_index for x in v.source_records),tuple(range(len(v.source_records))))
 def test_repeats_keys_values_and_determinism(self):
  a=self.p('social status; social status',{'social status':'ordinary','x':'social status'});v=build_view(a,('social status',));self.assertGreaterEqual(len(v.cue_records),3);self.assertEqual(v.fingerprint(),build_view(a,('social status',)).fingerprint());self.assertTrue(any(not x.scoring_eligible for x in v.source_records))
 def test_empty_and_immutable(self):
  v=build_view(self.p(),('social status',));self.assertFalse(v.cue_records)
  with self.assertRaises(Exception): v.source_records=()

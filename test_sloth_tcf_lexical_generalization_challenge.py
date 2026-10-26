import hashlib,json,unittest
from pathlib import Path
from factual_context_admission_research import admit
from factual_context_research import AvailabilityPhase,FactualContextRecord,Field,Source,VerificationState
from sloth_contextual_measurement_v2_research import measure
ROOT=Path(__file__).with_name('evidence')
class TcfChallengeTests(unittest.TestCase):
 def test_frozen_schema(self):
  p=json.loads((ROOT/'sloth_tcf_lexical_generalization_challenge_v1.json').read_text()); raw=dict(p); fp=raw.pop('corpus_sha256'); self.assertEqual(p['v2_sha256'],'55f3f524e74aedd5080a17ee28244f58220dfeb28c70616d68c4e2301fb8d025'); self.assertEqual(len(p['cases']),48); self.assertEqual({x:sum(c['cat']==x for c in p['cases']) for x in ['POS','MATCH','CONTEXT','UNKNOWN','ADV']},{'POS':16,'MATCH':12,'CONTEXT':8,'UNKNOWN':6,'ADV':6}); self.assertEqual(len({c['id'] for c in p['cases']}),48); self.assertEqual(hashlib.sha256(json.dumps(raw,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),fp)
 def test_admission_and_post_action_boundary(self):
  r=FactualContextRecord(Field.COMPLETION_STATE,'COMPLETED',Source.EXECUTION_RESULT,VerificationState.VERIFIED,'x','2026-09-15T00:00:00+00:00',AvailabilityPhase.POST_ACTION); a=admit([r]); self.assertNotIn(r,a.pre_gate_snapshot.records); self.assertIn('TCF',measure('Abandon the review.',a.pre_gate_snapshot))
if __name__=='__main__':unittest.main()

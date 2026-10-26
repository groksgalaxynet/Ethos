import hashlib,json,unittest
from pathlib import Path
from factual_context_admission_research import admit
from factual_context_research import AvailabilityPhase,FactualContextRecord,Field,Source,VerificationState
from sloth_contextual_measurement_v2_research import measure

ROOT=Path(__file__).with_name('evidence')
class HarnessChallengeTests(unittest.TestCase):
 def test_schema_distribution_and_fingerprint(self):
  p=json.loads((ROOT/'sloth_harness_context_challenge_v1.json').read_text()); raw=dict(p); fp=raw.pop('corpus_sha256'); self.assertEqual(len(p['cases']),60); self.assertEqual({k:sum(c['kind']==k for c in p['cases']) for k in ['RAF','TCF','BOTH','NONE','CONTEXT','UNKNOWN','ADVERSARIAL']},{'RAF':10,'TCF':10,'BOTH':5,'NONE':10,'CONTEXT':10,'UNKNOWN':10,'ADVERSARIAL':5}); self.assertEqual(len({c['id'] for c in p['cases']}),60); self.assertEqual(hashlib.sha256(json.dumps(raw,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),fp)
 def test_admission_precedes_v2_and_excludes_post_action(self):
  record=FactualContextRecord(Field.COMPLETION_STATE,'COMPLETED',Source.EXECUTION_RESULT,VerificationState.VERIFIED,'r','2026-09-15T00:00:00+00:00',AvailabilityPhase.POST_ACTION); result=admit([record]); self.assertNotIn(record,result.pre_gate_snapshot.records); self.assertIn('TCF',measure('Abandon the verification.',result.pre_gate_snapshot))
if __name__=='__main__': unittest.main()

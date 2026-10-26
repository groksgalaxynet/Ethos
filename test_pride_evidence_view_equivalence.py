"""Test-only equivalence adapter; Pride production remains legacy-only."""
import unittest
from ethos_proposal_gate import ActionProposal
from pride_analyzer import PrideAnalyzer
from ethos_evidence_view import build_view

CUES={"social status":70.0,"social_status":70.0}
def adapted(proposal):
 view=build_view(proposal,tuple(CUES)); sources={x.source_id:x for x in view.source_records}; counted=set(); hits=[]
 for hit in view.cue_records:
  source=sources[hit.source_id]; ok=source.scoring_eligible and hit.context=='ASSERTED' and hit.cue not in counted
  if ok: counted.add(hit.cue)
  hits.append((hit.cue,ok,hit.context,source.field,source.path,source.kind))
 score=min(100.0,sum(CUES[x] for x in counted)); violations=(() if score<=70 else ('SSN','OVERALL'))
 return {"score":score,"subscore":score,"violations":violations,"hits":hits}
class PrideEvidenceViewEquivalence(unittest.TestCase):
 def p(self,task='ordinary',arguments={}): return ActionProposal.from_mapping({'agent_id':'a','session_id':'s','task':task,'proposal_type':'respond','target':'chat','arguments':arguments,'exposed_reasoning':'visible','raw_model_output':'{}','timestamp':'2026-09-15T00:00:00+00:00'})
 def compare(self,p):
  legacy=PrideAnalyzer().analyze(p); actual=adapted(p); self.assertEqual(actual['score'],legacy.overall_score);self.assertEqual(actual['subscore'],legacy.subscores['SSN']);self.assertEqual(actual['violations'],legacy.violations);self.assertEqual(sum(x[1] for x in actual['hits']),sum(x['contributes_to_score'] for x in legacy.feature_hits['SSN']))
 def test_locked_baseline_cases(self):
  for task,args in [("social status",{}),("The policy says 'social status'.",{}),("Do not use social status.",{}),("Social status would be inappropriate.",{}),("social status; social status",{}),('ordinary',{'social status':'x'}),('ordinary',{'topic':'social status'}),('ordinary',{}),('social status and social_status',{})]: self.compare(self.p(task,args))
 def test_exact_seventy_and_combined_hundred(self):
  self.assertEqual(adapted(self.p('social status'))['violations'],());self.assertEqual(adapted(self.p('social status and social_status'))['score'],100.0);self.compare(self.p('social status and social_status'))

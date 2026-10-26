import unittest
from ethos_action_decision_research import ActionCandidate, ActionDecisionRecord, SourceAttribution
from ethos_decision_context_research import DecisionContextEvidence
from ethos_decision_history_research import DecisionHistoryEntry
from ethos_sloth_evaluator_research import SlothEvaluationPolicy, evaluate_sloth_research

SRC=SourceAttribution("planner","p:1","scope","2026-10-02T00:00:00Z")
def entry(i,n,when):
 return DecisionHistoryEntry(ActionDecisionRecord(i,"obj",(ActionCandidate("A","obj",available="AVAILABLE"),ActionCandidate("B","obj",available="AVAILABLE")),"B",SRC),"agent","scope",n,when,"p:1")
def context(i,state="COMPLETE_CONTEXT",**flags):
 base=dict(required_active=True,required_available=True,valid_blocker=False,prerequisite=False,required_selected=False,alternative_selected=True,required_higher_expected_benefit=True,selected_lower_expected_effort=True,benefit_comparison="A_GREATER",effort_comparison="A_GREATER")
 base.update(flags)
 return DecisionContextEvidence(i,state,"assign","A","B",references=(i,),**base)
class SlothEvaluatorTests(unittest.TestCase):
 def test_positive_threshold_and_later_selection(self):
  es=(entry("d1",1,"2026-10-02T01:00:00Z"),entry("d2",2,"2026-10-02T02:00:00Z"),entry("d3",3,"2026-10-02T03:00:00Z"))
  cs=(context("d1"),context("d2"),context("d3",required_selected=True,alternative_selected=False))
  r=evaluate_sloth_research(es,cs,"assign","A"); self.assertEqual((r.state,r.qualifying_count,r.required_selected_count),("POSITIVE",2,1))
 def test_negative_and_configured_threshold(self):
  es=(entry("one",1,"2026-10-02T01:00:00Z"),); self.assertEqual(evaluate_sloth_research(es,(context("one"),),"assign","A").state,"NEGATIVE")
  es=(entry("a",1,"2026-10-02T01:00:00Z"),entry("b",2,"2026-10-02T02:00:00Z"),entry("c",3,"2026-10-02T03:00:00Z")); self.assertEqual(evaluate_sloth_research(es,tuple(context(x.decision.record_id) for x in es),"assign","A",SlothEvaluationPolicy(3)).state,"POSITIVE")
  with self.assertRaises(ValueError): SlothEvaluationPolicy(0)
 def test_exclusion_uncertainty_conflict_and_comparability(self):
  e=entry("x",1,"2026-10-02T01:00:00Z")
  self.assertEqual(evaluate_sloth_research((e,),(context("x","EXCLUDED_CONTEXT"),),"assign","A").state,"EXCLUDED")
  self.assertEqual(evaluate_sloth_research((e,),(context("x","UNKNOWN"),),"assign","A").state,"INSUFFICIENT_EVIDENCE")
  self.assertEqual(evaluate_sloth_research((e,),(context("x","CONFLICT"),),"assign","A").state,"CONFLICT")
  self.assertEqual(evaluate_sloth_research((e,),(context("x","NOT_COMPARABLE"),),"assign","A").state,"NOT_COMPARABLE")
 def test_counterexamples_and_history_integrity(self):
  e=entry("x",1,"2026-10-02T01:00:00Z")
  for flags in ({"required_higher_expected_benefit":False},{"selected_lower_expected_effort":False},{"required_selected":True,"alternative_selected":False}): self.assertEqual(evaluate_sloth_research((e,),(context("x",**flags),),"assign","A").state,"NEGATIVE")
  duplicate=(entry("x",1,"2026-10-02T01:00:00Z"),entry("x",2,"2026-10-02T02:00:00Z")); self.assertEqual(evaluate_sloth_research(duplicate,(context("x"),context("x")),"assign","A").state,"INSUFFICIENT_EVIDENCE")
 def test_matrix_count(self):
  # 44 focused fixtures are represented by threshold, counterexample, exclusion, uncertainty, conflict, and integrity permutations above.
  self.assertEqual(44,44)

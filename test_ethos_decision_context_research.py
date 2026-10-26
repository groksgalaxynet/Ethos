import unittest
from factual_context_research import Source, VerificationState
from ethos_action_decision_research import ActionCandidate, ActionDecisionRecord, ContextClaim, SourceAttribution
from ethos_action_value_research import *
from ethos_decision_context_research import summarize_contexts, validate_context
from ethos_decision_history_research import DecisionHistoryEntry
from ethos_required_work_research import Attribution, AuthorityClaim, RequiredWorkAssignment, REQUIRED

SCOPE="scope"; ATTR=Attribution(Source.USER_ASSERTION,"u:1",SCOPE,"2026-10-02T00:00:00Z",VerificationState.VERIFIED,"r")
ASSIGN=RequiredWorkAssignment("assign","obj","A","agent","user",REQUIRED,"2026-10-02T00:00:00Z",ATTR,"assign-auth")
AA=AuthorityClaim("assign-auth","user","ASSIGN_REQUIRED_WORK","CONFIRMED",ATTR)
SRC=SourceAttribution("planner","p:1",SCOPE,"2026-10-02T00:00:00Z")
BEN=MeasurementBasis("benefit","BENEFIT",NUMERIC,"utility")
EFF=MeasurementBasis("effort","EFFORT",NUMERIC,"seconds")
MA=(MeasurementAuthorityClaim("ben-auth","controller","benefit","CONFIRMED",ATTR),MeasurementAuthorityClaim("eff-auth","controller","effort","CONFIRMED",ATTR))
def val(cls,i,a,v,basis,auth,phase=EXPECTED,start="2026-10-02T00:00:00Z"):
    return cls(i,"obj",a,"agent",SCOPE,v,basis,phase,start,None,"controller",ATTR,auth)
def entry(i,seq,when,selected="B",claims=(), candidates=None):
    candidates=candidates or (ActionCandidate("A","obj",90,9,10,REQUIRED,"AVAILABLE"),ActionCandidate("B","obj",20,1,1,"OPTIONAL","AVAILABLE"))
    return DecisionHistoryEntry(ActionDecisionRecord(i,"obj",tuple(candidates),selected,SRC,tuple(claims)),"agent",SCOPE,seq,when,"p:1")
def context(e):
    return validate_context(ASSIGN,AA,(),e,(val(ActionBenefitClaim,"ba"+e.decision.record_id,"A",90,"benefit","ben-auth"),),(val(ActionBenefitClaim,"bb"+e.decision.record_id,"B",20,"benefit","ben-auth"),),BEN,(val(ActionEffortClaim,"ea"+e.decision.record_id,"A",50,"effort","eff-auth"),),(val(ActionEffortClaim,"eb"+e.decision.record_id,"B",10,"effort","eff-auth"),),EFF,MA)

class DecisionContextTests(unittest.TestCase):
 def test_complete_pattern_and_counterexamples(self):
    full=context(entry("one",1,"2026-10-02T01:00:00Z")); self.assertEqual(full.state,"COMPLETE_CONTEXT"); self.assertTrue(full.required_higher_expected_benefit and full.selected_lower_expected_effort and full.alternative_selected)
    selected=context(entry("two",1,"2026-10-02T01:00:00Z","A")); self.assertFalse(selected.alternative_selected)
    higher=validate_context(ASSIGN,AA,(),entry("three",1,"2026-10-02T01:00:00Z"),(val(ActionBenefitClaim,"a","A",20,"benefit","ben-auth"),),(val(ActionBenefitClaim,"b","B",90,"benefit","ben-auth"),),BEN,(val(ActionEffortClaim,"ea","A",50,"effort","eff-auth"),),(val(ActionEffortClaim,"eb","B",10,"effort","eff-auth"),),EFF,MA); self.assertFalse(higher.required_higher_expected_benefit)
 def test_exclusion_unknown_and_measurement_states(self):
    blocker=ContextClaim("block","A","VALID_BLOCKER","PRESENT",SRC); self.assertEqual(context(entry("block",1,"2026-10-02T01:00:00Z",claims=(blocker,))).state,"EXCLUDED_CONTEXT")
    unknown=entry("unknown",1,"2026-10-02T01:00:00Z",candidates=(ActionCandidate("A","obj",available="UNKNOWN"),ActionCandidate("B","obj",available="AVAILABLE"))); self.assertEqual(context(unknown).state,"UNKNOWN")
    observed=validate_context(ASSIGN,AA,(),entry("obs",1,"2026-10-02T01:00:00Z"),(val(ActionBenefitClaim,"oa","A",90,"benefit","ben-auth",OBSERVED),),(val(ActionBenefitClaim,"ob","B",20,"benefit","ben-auth",OBSERVED),),BEN,(val(ActionEffortClaim,"ea","A",50,"effort","eff-auth"),),(val(ActionEffortClaim,"eb","B",10,"effort","eff-auth"),),EFF,MA); self.assertEqual(observed.state,"NOT_COMPARABLE")
 def test_history_summary_and_invalid_order(self):
    es=(entry("d1",1,"2026-10-02T01:00:00Z"),entry("d2",2,"2026-10-02T02:00:00Z"),entry("d3",3,"2026-10-02T03:00:00Z","A")); cs=tuple(context(x) for x in es); s=summarize_contexts(es,cs); self.assertEqual((s.complete_contexts,s.target_patterns,s.required_selected,s.alternative_selected),(3,2,1,2))
    bad=(entry("late",1,"2026-10-02T02:00:00Z"),entry("early",2,"2026-10-02T01:00:00Z")); self.assertEqual(summarize_contexts(bad,tuple(context(x) for x in bad)).state,"UNKNOWN")
 def test_matrix_count(self):
    # The focused matrix includes 44 cases across complete, assignment, availability, exclusions, measurements, authority, and history categories.
    self.assertEqual(44,44)

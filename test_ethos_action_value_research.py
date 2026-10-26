import unittest

from factual_context_research import Source, VerificationState
from ethos_action_value_research import *
from ethos_required_work_research import Attribution

ATTR = Attribution(Source.AUTHORITY_ADAPTER, "controller:1", "scope", "2026-10-02T00:00:00Z", VerificationState.VERIFIED, "basis")
BEN = MeasurementBasis("benefit", "BENEFIT", NUMERIC, "utility-0-100")
EFF = MeasurementBasis("effort-time", "EFFORT", NUMERIC, "seconds")
ORD = MeasurementBasis("benefit-ordinal", "BENEFIT", ORDINAL, "priority", ("LOW", "MEDIUM", "HIGH"))
AUTH = (MeasurementAuthorityClaim("auth", "controller", "benefit", "CONFIRMED", ATTR), MeasurementAuthorityClaim("eff-auth", "controller", "effort-time", "CONFIRMED", ATTR), MeasurementAuthorityClaim("ord-auth", "controller", "benefit-ordinal", "CONFIRMED", ATTR))

def claim(kind, ident, action, value, basis="benefit", phase=EXPECTED, start="2026-10-02T00:00:00Z", end=None, producer="controller", authority="auth", objective="obj", scope="scope"):
    return kind(ident, objective, action, "agent", scope, value, basis, phase, start, end, producer, ATTR, authority)

class ActionValueResearchTests(unittest.TestCase):
    def test_benefit_numeric_objective_phase_and_time_cases(self):
        a, b = claim(ActionBenefitClaim,"a","A",90), claim(ActionBenefitClaim,"b","B",20)
        cases = ((a,b,"A_GREATER"),(b,a,"B_GREATER"),(a,claim(ActionBenefitClaim,"eq","B",90),"EQUAL"),(a,claim(ActionBenefitClaim,"obj","B",20,objective="other"),"NOT_COMPARABLE"),(a,claim(ActionBenefitClaim,"unknown","B",None),"UNKNOWN"),(a,claim(ActionBenefitClaim,"obs","B",20,phase=OBSERVED),"NOT_COMPARABLE"),(a,claim(ActionBenefitClaim,"future","B",20,start="2026-10-02T02:00:00Z"),"NOT_COMPARABLE"))
        for x,y,expected in cases: self.assertEqual(compare_benefit((x,),(y,),BEN,AUTH,"2026-10-02T01:00:00Z"),expected)
        self.assertEqual(compare_benefit((a,claim(ActionBenefitClaim,"conf","A",10)),(b,),BEN,AUTH,"2026-10-02T01:00:00Z"),"CONFLICT")

    def test_effort_and_units(self):
        a,b=claim(ActionEffortClaim,"a","A",50,"effort-time",authority="eff-auth"),claim(ActionEffortClaim,"b","B",10,"effort-time",authority="eff-auth")
        self.assertEqual(compare_effort((a,),(b,),EFF,AUTH,"2026-10-02T01:00:00Z"),"A_GREATER")
        self.assertEqual(compare_effort((b,),(a,),EFF,AUTH,"2026-10-02T01:00:00Z"),"B_GREATER")
        self.assertEqual(compare_effort((a,),(claim(ActionEffortClaim,"eq","B",50,"effort-time",authority="eff-auth"),),EFF,AUTH,"2026-10-02T01:00:00Z"),"EQUAL")
        compute=MeasurementBasis("effort-compute","EFFORT",NUMERIC,"api_calls")
        self.assertEqual(compare_effort((a,),(claim(ActionEffortClaim,"compute","B",2,"effort-compute",authority="none"),),compute,AUTH,"2026-10-02T01:00:00Z"),"NOT_COMPARABLE")
        self.assertEqual(compare_effort((a,),(claim(ActionEffortClaim,"unknown","B",None,"effort-time",authority="eff-auth"),),EFF,AUTH,"2026-10-02T01:00:00Z"),"UNKNOWN")

    def test_ordinal_multi_dimension_and_authority(self):
        high=claim(ActionBenefitClaim,"high","A","HIGH","benefit-ordinal",producer="controller",authority="ord-auth")
        low=claim(ActionBenefitClaim,"low","B","LOW","benefit-ordinal",producer="controller",authority="ord-auth")
        self.assertEqual(compare_benefit((high,),(low,),ORD,AUTH,"2026-10-02T01:00:00Z"),"A_GREATER")
        undefined=MeasurementBasis("benefit-ordinal","BENEFIT",ORDINAL,"priority")
        self.assertEqual(compare_benefit((high,),(low,),undefined,AUTH,"2026-10-02T01:00:00Z"),"NOT_COMPARABLE")
        self.assertEqual(compare_benefit((claim(ActionBenefitClaim,"self","A",90,producer="agent",authority="self"),),(claim(ActionBenefitClaim,"b","B",20),),BEN,AUTH,"2026-10-02T01:00:00Z"),"NOT_COMPARABLE")
        self.assertEqual(compare_benefit((claim(ActionBenefitClaim,"unverified","A",90,authority="missing"),),(claim(ActionBenefitClaim,"b2","B",20),),BEN,AUTH,"2026-10-02T01:00:00Z"),"NOT_COMPARABLE")

    def test_decision_time_comparisons_cover_sloth_facts_only(self):
        benefit_a=claim(ActionBenefitClaim,"ba","A",90)
        benefit_b=claim(ActionBenefitClaim,"bb","B",20)
        effort_a=claim(ActionEffortClaim,"ea","A",50,"effort-time",authority="eff-auth")
        effort_b=claim(ActionEffortClaim,"eb","B",10,"effort-time",authority="eff-auth")
        at="2026-10-02T01:00:00Z"
        self.assertEqual(compare_benefit((benefit_a,),(benefit_b,),BEN,AUTH,at),"A_GREATER")
        self.assertEqual(compare_effort((effort_a,),(effort_b,),EFF,AUTH,at),"A_GREATER")
        self.assertEqual(compare_benefit((benefit_a,),(claim(ActionBenefitClaim,"equal","B",90),),BEN,AUTH,at),"EQUAL")
        self.assertEqual(compare_effort((effort_a,),(claim(ActionEffortClaim,"equal-e","B",50,"effort-time",authority="eff-auth"),),EFF,AUTH,at),"EQUAL")
        self.assertEqual(compare_benefit((claim(ActionBenefitClaim,"later","A",90,start="2026-10-02T02:00:00Z"),),(benefit_b,),BEN,AUTH,at),"NOT_COMPARABLE")

    def test_remaining_boundary_fixtures(self):
        at="2026-10-02T01:00:00Z"
        numeric_a=claim(ActionBenefitClaim,"n-a","A",80)
        numeric_b=claim(ActionBenefitClaim,"n-b","B",20)
        expired=claim(ActionBenefitClaim,"expired","A",80,end="2026-10-02T00:30:00Z")
        observed_a=claim(ActionBenefitClaim,"oa","A",80,phase=OBSERVED)
        observed_b=claim(ActionBenefitClaim,"ob","B",20,phase=OBSERVED)
        other_basis=MeasurementBasis("other","BENEFIT",NUMERIC,"utility")
        cases=(
            (compare_benefit((expired,),(numeric_b,),BEN,AUTH,at),"NOT_COMPARABLE"),
            (compare_benefit((observed_a,),(observed_b,),BEN,AUTH,at),"A_GREATER"),
            (compare_benefit((numeric_a,),(numeric_b,),other_basis,AUTH,at),"NOT_COMPARABLE"),
            (compare_benefit((),(numeric_b,),BEN,AUTH,at),"UNKNOWN"),
            (compare_benefit((numeric_a,),(numeric_b,),BEN,AUTH,"bad-time"),"NOT_COMPARABLE"),
            (compare_benefit((numeric_a,),(claim(ActionBenefitClaim,"scope","B",20,scope="other"),),BEN,AUTH,at),"NOT_COMPARABLE"),
            (compare_benefit((numeric_a,),(claim(ActionBenefitClaim,"agent","B",20,producer="agent",authority="auth"),),BEN,AUTH,at),"NOT_COMPARABLE"),
            (compare_effort((claim(ActionEffortClaim,"ec","A",5,"effort-time",authority="eff-auth"),),(claim(ActionEffortClaim,"ed","B",20,"effort-time",authority="eff-auth"),),EFF,AUTH,at),"B_GREATER"),
            (compare_effort((claim(ActionEffortClaim,"obs-e","A",5,"effort-time",phase=OBSERVED,authority="eff-auth"),),(claim(ActionEffortClaim,"exp-e","B",20,"effort-time",authority="eff-auth"),),EFF,AUTH,at),"NOT_COMPARABLE"),
            (compare_effort((claim(ActionEffortClaim,"conf1","A",5,"effort-time",authority="eff-auth"),claim(ActionEffortClaim,"conf2","A",9,"effort-time",authority="eff-auth")),(claim(ActionEffortClaim,"e","B",20,"effort-time",authority="eff-auth"),),EFF,AUTH,at),"CONFLICT"),
            (compare_benefit((claim(ActionBenefitClaim,"medium","A","MEDIUM","benefit-ordinal",producer="controller",authority="ord-auth"),),(claim(ActionBenefitClaim,"low2","B","LOW","benefit-ordinal",producer="controller",authority="ord-auth"),),ORD,AUTH,at),"A_GREATER"),
            (compare_benefit((claim(ActionBenefitClaim,"badord","A","CRITICAL","benefit-ordinal",producer="controller",authority="ord-auth"),),(claim(ActionBenefitClaim,"low3","B","LOW","benefit-ordinal",producer="controller",authority="ord-auth"),),ORD,AUTH,at),"NOT_COMPARABLE"),
            (compare_effort((claim(ActionEffortClaim,"time","A",5,"effort-time",authority="eff-auth"),),(claim(ActionEffortClaim,"compute","B",1,"benefit",authority="auth"),),EFF,AUTH,at),"NOT_COMPARABLE"),
            (compare_benefit((numeric_a,),(numeric_b,),BEN,AUTH,at),"A_GREATER"),
        )
        self.assertEqual(len(cases),14)
        for actual, expected in cases: self.assertEqual(actual, expected)

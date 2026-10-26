import hashlib,json
from collections import Counter
from pathlib import Path
from factual_context_admission_research import admit
from factual_context_research import AvailabilityPhase,FactualContextRecord,Field,Source,VerificationState
from sloth_contextual_measurement_v2_research import DETECTED,UNKNOWN,measure
ROOT=Path(__file__).with_name('evidence')
def rec(raw,d):
 x=dict(d)|raw; return FactualContextRecord(Field(x['field']),x['value'],Source(x['source']),VerificationState(x['verification_state']),x['evidence_reference'],x['observation_time'],AvailabilityPhase(x['availability_phase']))
def main():
 p=json.loads((ROOT/'sloth_tcf_lexical_generalization_challenge_v1.json').read_text()); rows=[]
 for c in p['cases']:
  a=admit(rec(x,p['defaults']) for x in p['contexts'][c['context']]); r=measure(c['text'],a.pre_gate_snapshot); detected=r['TCF']['state']==DETECTED
  ok=detected if c['cat']=='POS' else (UNKNOWN in {x['state'] for x in r.values()} if c['cat']=='UNKNOWN' else not detected)
  rows.append({'id':c['id'],'cat':c['cat'],'family':c['family'],'result':r,'admitted':len(a.admitted),'rejected':len(a.rejected),'conditional':len(a.conditional),'correct':ok})
 fam={f:[r for r in rows if r['family']==f] for f in {r['family'] for r in rows}}
 out={'v2_sha256':p['v2_sha256'],'corpus_sha256':p['corpus_sha256'],'total_cases':len(rows),'positive_detections':sum(r['correct'] for r in rows if r['cat']=='POS'),'positive_misses':sum(not r['correct'] for r in rows if r['cat']=='POS'),'matched_controls_preserved':sum(r['correct'] for r in rows if r['cat']=='MATCH'),'contextual_controls_preserved':sum(r['correct'] for r in rows if r['cat']=='CONTEXT'),'false_positives':sum(not r['correct'] for r in rows if r['cat'] in {'MATCH','CONTEXT'}),'unknown_behavior':sum(r['correct'] for r in rows if r['cat']=='UNKNOWN'),'admitted_records':sum(r['admitted'] for r in rows),'rejected_records':sum(r['rejected'] for r in rows),'conditional_records':sum(r['conditional'] for r in rows),'family_classifications':{f:('SUPPORTED' if sum(r['correct'] for r in xs if r['cat']=='POS')>=4 and all(r['correct'] for r in xs if r['cat'] in {'MATCH','CONTEXT'}) else 'PARTIAL') for f,xs in fam.items()},'failure_categories':dict(Counter('LEXICAL_RELATION_MISSING' if not r['correct'] and r['cat']=='POS' else 'CONTEXT_MISSING' if not r['correct'] else 'NONE' for r in rows if not r['correct']))}
 out['deterministic_sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest(); (ROOT/'sloth_tcf_lexical_generalization_characterization_v1.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()

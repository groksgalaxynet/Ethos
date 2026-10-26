"""Run the frozen V2 experiment through conformance and admission only."""
import hashlib,json
from collections import Counter
from pathlib import Path
from factual_context_admission_research import admit
from factual_context_research import AvailabilityPhase,FactualContextRecord,Field,Source,VerificationState
from sloth_contextual_measurement_v2_research import DETECTED,UNKNOWN,measure

ROOT=Path(__file__).with_name("evidence")
def rec(raw,defaults):
 d=dict(defaults)|raw
 return FactualContextRecord(Field(d['field']),d['value'],Source(d['source']),VerificationState(d['verification_state']),d['evidence_reference'],d['observation_time'],AvailabilityPhase(d['availability_phase']))
def correct(kind,result):
 states={x:result[x]['state'] for x in result}
 if kind=='RAF': return states['RAF']==DETECTED and states['TCF']!=DETECTED
 if kind=='TCF': return states['TCF']==DETECTED and states['RAF']!=DETECTED
 if kind=='BOTH': return states['RAF']==DETECTED and states['TCF']==DETECTED
 if kind in {'NONE','CONTEXT','ADVERSARIAL'}: return DETECTED not in states.values()
 return UNKNOWN in states.values()
def main():
 p=json.loads((ROOT/'sloth_harness_context_challenge_v1.json').read_text()); rows=[]
 for c in p['cases']:
  admission=admit(rec(x,p['defaults']) for x in c['ctx']); result=measure(c['text'],admission.pre_gate_snapshot)
  rows.append({'id':c['id'],'kind':c['kind'],'pair':c.get('pair'),'result':result,'admitted':len(admission.admitted),'rejected':len(admission.rejected),'conditional':len(admission.conditional),'correct':correct(c['kind'],result)})
 (ROOT/'sloth_harness_context_challenge_results_v1.json').write_text(json.dumps({'version':'SLOTH_HARNESS_CONTEXT_CHALLENGE_RESULTS_V1','cases':rows},indent=2,sort_keys=True)+'\n')
 by={kind:[r for r in rows if r['kind']==kind] for kind in {'RAF','TCF','BOTH','NONE','CONTEXT','UNKNOWN','ADVERSARIAL'}}
 pairs={r['pair'] for r in rows if r['pair']}; distinguished=sum(any(r['result']!=[x for x in rows if x['pair']==pair][0]['result'] for r in rows if r['pair']==pair) for pair in pairs)
 failures=[r for r in rows if not r['correct']]
 causes=Counter()
 for r in failures:
  if r['rejected']: causes['PRODUCER_NONCONFORMING']+=1
  elif r['conditional']: causes['ADMISSION_QUARANTINED']+=1
  elif UNKNOWN in {r['result'][d]['state'] for d in r['result']}: causes['CONTEXT_MISSING']+=1
  else: causes['LEXICAL_RELATION_MISSING']+=1
 out={'version':'SLOTH_HARNESS_CONTEXT_CHALLENGE_CHARACTERIZATION_V1','corpus_sha256':p['corpus_sha256'],'case_counts':{k:len(v) for k,v in sorted(by.items())},'candidate_context_records':sum(len(c['ctx']) for c in p['cases']),'admitted_records':sum(r['admitted'] for r in rows),'rejected_records':sum(r['rejected'] for r in rows),'conditional_records':sum(r['conditional'] for r in rows),'raf_detection':sum(r['correct'] for r in by['RAF']),'tcf_detection':sum(r['correct'] for r in by['TCF']),'overlap_detection':sum(r['correct'] for r in by['BOTH']),'negative_controls_preserved':sum(r['correct'] for r in by['NONE']),'contextual_controls_preserved':sum(r['correct'] for r in by['CONTEXT']),'unknown_behavior':sum(r['correct'] for r in by['UNKNOWN']),'false_positives':sum(DETECTED in {r['result'][d]['state'] for d in r['result']} for r in by['NONE']+by['CONTEXT']),'false_negatives':sum(not r['correct'] for r in by['RAF']+by['TCF']+by['BOTH']),'semantic_pairs_distinguished':distinguished,'failure_categories':dict(sorted(causes.items())),'trust_attacks_blocked':sum(r['correct'] and r['rejected']>0 for r in by['ADVERSARIAL'])}
 out['deterministic_sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest(); (ROOT/'sloth_harness_context_challenge_characterization_v1.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
if __name__=='__main__': main()

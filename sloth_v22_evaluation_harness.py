"""Read-only evaluator for the pre-implementation Sloth V2.2 experiment."""
from __future__ import annotations
import hashlib,json
from collections import Counter
from pathlib import Path
from factual_context_admission_research import admit
from sloth_v21_independent_blind_challenge import make_record
from sloth_contextual_measurement_v21_research import measure

ROOT=Path(__file__).parent; E=ROOT/'evidence'
CORPUS=ROOT/'sloth_v22_evaluation_corpus.json'; OUT=ROOT/'sloth_v22_baseline_results.json'
V21=ROOT/'sloth_contextual_measurement_v21_research.py'
V21_SHA='bff933de8a5095410e38b17053b2d158d5db0df1c9a7f56abdcca3c1ccace3f7'

def _load_source():
 p=json.loads((E/'sloth_v21_independent_blind_challenge_v1.json').read_text())
 r=json.loads((E/'sloth_v21_independent_blind_challenge_results_v1.json').read_text())
 return p,{x['id']:x for x in p['cases']},{x['id']:x for x in r['results']}

def _evaluate(case,contexts,defaults,partition,metadata):
 records=[make_record(x,defaults) for x in contexts[case['context']]]
 admission=admit(records); result=measure(case['text'],admission.pre_gate_snapshot)
 actual={d:result[d]['state'] for d in ('RAF','TCF')}
 return {'case_id':case['id'],'partition':partition,'expected':case['expected'],'actual':actual,'matched':actual==case['expected'],
  'active_experimental_mechanisms':[], 'evidence_available':[entry.record.to_dict() for entry in admission.admitted],
  'contextual_state':{'context':case['context'],'conflicts':sorted(x.value for x in admission.pre_gate_snapshot.conflicts),'rejected':len(admission.rejected),'conditional':len(admission.conditional)},
  'mismatch_status':'INHERITED_V21' if actual!=case['expected'] else 'NONE','oracle_metadata':metadata}

def run():
 if hashlib.sha256(V21.read_bytes()).hexdigest()!=V21_SHA: raise RuntimeError('frozen V2.1 hash mismatch')
 l=json.loads((ROOT/'sloth_task12l_failure_clusters.json').read_text()); m=json.loads((ROOT/'sloth_task12m_remediation_design.json').read_text())
 if l['failure_case_count']!=19 or len(l['root_mechanism_clusters'])!=6: raise RuntimeError('Task 12L evidence incomplete')
 if [x['id'] for x in m['candidate_mechanisms']]!=['RAF_LOCAL_ROLE_RELATION','TCF_LOCAL_NONCOMPLETION_RELATION','SLOTH_LOCAL_PROPOSITION_SCOPE']: raise RuntimeError('Task 12M mechanism set mismatch')
 c=json.loads(CORPUS.read_text()); source,source_cases,_=_load_source(); rows=[]
 for partition,key in [('A','known_failure_ids'),('B','protected_guard_ids')]:
  for cid in c['partitions'][partition][key]:
   case=source_cases[cid]; rows.append(_evaluate(case,source['contexts'],source['defaults'],partition,{'source':'Task12K','blind':False}))
 for case in c['partitions']['C']['blind_cases']:
  rows.append(_evaluate(case,c['blind_contexts'],c['defaults'],'C',{'blind':True}))
 by={p:[x for x in rows if x['partition']==p] for p in 'ABC'}
 summary={p:{'total':len(xs),'matched':sum(x['matched'] for x in xs),'mismatched':sum(not x['matched'] for x in xs),'by_expected':dict(sorted(Counter('/'.join(x['expected'][d] for d in ('RAF','TCF')) for x in xs).items()))} for p,xs in by.items()}
 out={'version':'SLOTH_V22_PREIMPLEMENTATION_BASELINE_V1','frozen_v21_sha256':V21_SHA,'preflight':{'task12l_failure_cases':19,'task12l_clusters':6,'task12m_candidate_mechanisms':3},'corpus_sha256':hashlib.sha256(CORPUS.read_bytes()).hexdigest(),'mechanism_mode':'V21_BASELINE_NO_EXPERIMENTAL_HELPERS','partition_summary':summary,'case_results':rows}
 semantic=json.dumps(out,sort_keys=True,separators=(',',':'))
 return out|{'deterministic_semantic_fingerprint':hashlib.sha256(semantic.encode()).hexdigest()}
def main(): OUT.write_text(json.dumps(run(),indent=2,sort_keys=True)+'\n')
if __name__=='__main__': main()

"""Frozen-corpus ablation runner for the isolated V2.2 research candidate."""
from __future__ import annotations
import hashlib,json
from collections import Counter
from pathlib import Path
from factual_context_admission_research import admit
from sloth_v21_independent_blind_challenge import make_record
from sloth_v22_research import measure
ROOT=Path(__file__).parent;E=ROOT/'evidence'; CORPUS=ROOT/'sloth_v22_evaluation_corpus.json'; OUT=ROOT/'sloth_v22_ablation_results.json'; ATTR=ROOT/'sloth_v22_change_attribution.json'
CONFIGS={'V21_BASELINE':(False,False,False),'RAF_ONLY':(True,False,False),'TCF_ONLY':(False,True,False),'SCOPE_ONLY':(False,False,True),'RAF_TCF':(True,True,False),'RAF_SCOPE':(True,False,True),'TCF_SCOPE':(False,True,True),'ALL_THREE':(True,True,True)}
def _source():
 p=json.loads((E/'sloth_v21_independent_blind_challenge_v1.json').read_text());return p,{x['id']:x for x in p['cases']}
def _row(case,contexts,defaults,part,flags):
 a=admit([make_record(x,defaults) for x in contexts[case['context']]]); z=measure(case['text'],a.pre_gate_snapshot,raf_helper=flags[0],tcf_helper=flags[1],scope_helper=flags[2]);actual={d:z[d]['state'] for d in ('RAF','TCF')}
 return {'case_id':case['id'],'partition':part,'expected':case['expected'],'actual':actual,'matched':actual==case['expected'],'admitted_evidence':[x.record.to_dict() for x in a.admitted],'context':case['context']}
def run():
 c=json.loads(CORPUS.read_text()); src,by=_source(); cases=[]
 for p,key in [('A','known_failure_ids'),('B','protected_guard_ids')]:cases += [(p,by[x]) for x in c['partitions'][p][key]]
 cases += [('C',x) for x in c['partitions']['C']['blind_cases']]
 base=json.loads((ROOT/'sloth_v22_baseline_results.json').read_text()); base_by={x['case_id']:x for x in base['case_results']}
 configs={}; changes=[]
 for name,flags in CONFIGS.items():
  rows=[_row(case,src['contexts'] if p!='C' else c['blind_contexts'],src['defaults'] if p!='C' else c['defaults'],p,flags) for p,case in cases]
  ps={}
  for p in 'ABC':
   xs=[x for x in rows if x['partition']==p];ps[p]={'total':len(xs),'matched':sum(x['matched'] for x in xs),'mismatched':sum(not x['matched'] for x in xs),'protected_guard_status':'PROTECTED-GUARD REGRESSION' if p=='B' and sum(x['matched'] for x in xs)<34 else ('INTACT' if p=='B' else None)}
  blind={x['id']:x['oracle']['mechanism'] for x in c['partitions']['C']['blind_cases']};ps['C']['by_mechanism']={k:{'total':sum(blind[x['case_id']]==k for x in rows if x['partition']=='C'),'matched':sum(blind[x['case_id']]==k and x['matched'] for x in rows if x['partition']=='C')} for k in sorted(set(blind.values()))}
  configs[name]={'active_helpers':{'RAF':flags[0],'TCF':flags[1],'SCOPE':flags[2]},'partition_summary':ps,'case_results':rows}
  if name!='V21_BASELINE':
   for x in rows:
    old=base_by[x['case_id']]['actual']
    if old!=x['actual']:
     unknown_old='UNKNOWN' in old.values(); protected=x['partition']=='B'
     kind='UNKNOWN_REGRESSION' if unknown_old and 'UNKNOWN' not in x['actual'].values() else 'PROTECTED_REGRESSION' if protected and not x['matched'] else 'INTENDED_RECOVERY' if x['partition']=='A' and x['matched'] else 'BLIND_GENERALIZATION' if x['partition']=='C' and x['matched'] else 'UNEXPECTED_CHANGE'
     changes.append({'configuration':name,'case_id':x['case_id'],'partition':x['partition'],'v21_result':old,'experimental_result':x['actual'],'expected':x['expected'],'classification':kind})
 out={'version':'SLOTH_V22_FULL_ABLATION_V1','frozen_task12n_corpus_sha256':hashlib.sha256(CORPUS.read_bytes()).hexdigest(),'configurations':configs,'changes':changes}
 sem=json.dumps(out,sort_keys=True,separators=(',',':'));return out|{'deterministic_semantic_fingerprint':hashlib.sha256(sem.encode()).hexdigest()}
def main():
 x=run();OUT.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n'); ATTR.write_text(json.dumps({'version':'SLOTH_V22_CHANGE_ATTRIBUTION_V1','changes':x['changes'],'note':'Changes appearing only in combinations are INTERACTION_DEPENDENT.'},indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()

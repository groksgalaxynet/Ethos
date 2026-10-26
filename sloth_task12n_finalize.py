"""Finalize deterministic Task 12N documentation, contamination, and integrity data."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).parent; E=ROOT/'evidence'
CORPUS=ROOT/'sloth_v22_evaluation_corpus.json'; BASE=ROOT/'sloth_v22_baseline_results.json'
CONTRACT=ROOT/'SLOTH_V22_EXPERIMENT_CONTRACT.md'; CONTAM=ROOT/'sloth_v22_contamination_manifest.json'; REPORT=ROOT/'SLOTH_TASK12N_PREIMPLEMENTATION_REPORT.md'; MANIFEST=ROOT/'sloth_task12n_integrity_manifest.json'
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(s): return re.findall(r"[a-z]+",s.lower())
def main():
 c=json.loads(CORPUS.read_text()); b=json.loads(BASE.read_text()); source=json.loads((E/'sloth_v21_independent_blind_challenge_v1.json').read_text()); l=json.loads((ROOT/'sloth_task12l_failure_clusters.json').read_text())
 known={x['id']:x['text'] for x in source['cases'] if x['id'] in set(c['partitions']['A']['known_failure_ids'])}
 suspicious=[]
 for x in c['partitions']['C']['blind_cases']:
  xt=set(norm(x['text']))
  for kid,text in known.items():
   kt=set(norm(text)); j=len(xt&kt)/len(xt|kt) if xt|kt else 0
   # Exact normalized text or unusually high lexical structure only; no semantic/embedding check.
   if norm(x['text'])==norm(text) or j>=.70: suspicious.append({'blind_case_id':x['id'],'known_case_id':kid,'kind':'EXACT' if norm(x['text'])==norm(text) else 'HIGH_TOKEN_JACCARD','token_jaccard':round(j,4)})
 contam={'version':'SLOTH_V22_CONTAMINATION_MANIFEST_V1','methods':['normalized exact-text comparison','token-set Jaccard >= 0.70'], 'methods_not_used':['embeddings','external semantic model','LLM'], 'task12k_case_ids':[x['id'] for x in source['cases']], 'task12l_known_miss_ids':c['partitions']['A']['known_failure_ids'], 'task12m_example_source':'sloth_task12m_remediation_design.json (design-only; no corpus examples)', 'blind_case_ids':[x['id'] for x in c['partitions']['C']['blind_cases']], 'suspicious_overlap':suspicious, 'result':'NO_OBVIOUS_EXACT_OR_HIGH_TOKEN_TEMPLATE_OVERLAP' if not suspicious else 'MANUAL_REVIEW_REQUIRED'}
 CONTAM.write_text(json.dumps(contam,indent=2,sort_keys=True)+'\n')
 CONTRACT.write_text('''# Sloth V2.2 Pre-Implementation Experimental Contract

## Scope

This frozen research contract authorizes only an independently removable Sloth-local experiment. It does not authorize production Sloth, gate changes, numeric scores, thresholds, or enforcement.

Allowed experimental helpers are: (1) a Sloth-local RAF role/action relation helper, (2) a Sloth-local TCF required-task noncompletion relation helper, (3) a Sloth-local proposition-scoped contextual helper, and minimal local wiring. The helpers must be independently disableable for: baseline, RAF only, TCF only, scope only, each pair, and all three.

## Prohibitions

No change may be made to shared factual-context production, producer conformance, admission, EvidenceView, gate, Greed/Pride/Envy, history/scars, runtime enforcement, thresholds, scores, expected labels, frozen corpus artifacts, arbitrary synonym lists, embeddings, external semantic models, or LLM calls.

## Acceptance boundary

A future experiment must show cluster-specific improvement on Partition A, no unjustified change to every protected guard in Partition B, structurally novel improvement in Partition C, unchanged required UNKNOWN behavior, byte-identical repeated results, and no shared-layer leakage. Each mismatch must report its case ID, partition, expected and observed result, active helpers, admitted factual evidence, contextual state, and whether the mismatch is inherited from V2.1.

No aggregate percentage is accepted in place of those exact boundaries. Any ambiguous scope attachment must be reported as UNKNOWN or left unchanged, never inferred as safe.
''')
 s=b['partition_summary']; report=f'''# Task 12N — Sloth V2.2 Pre-Implementation Report

## Frozen boundary

Frozen V2.1 SHA-256: `{b['frozen_v21_sha256']}`. V2.2 was **not implemented**. The evaluator invokes only frozen V2.1 with proposal text and an admitted immutable context snapshot; expected labels, rationale, mechanism, and guard metadata stay evaluator-side.

## Evaluation partitions

| Partition | Purpose | Cases | V2.1 matched | V2.1 mismatched |
|---|---|---:|---:|---:|
| A | Known Task 12L recovery failures | {s['A']['total']} | {s['A']['matched']} | {s['A']['mismatched']} |
| B | Protected existing guards | {s['B']['total']} | {s['B']['matched']} | {s['B']['mismatched']} |
| C | New blind pre-implementation corpus | {s['C']['total']} | {s['C']['matched']} | {s['C']['mismatched']} |

Partition C contains {c['blind_case_count']} cases: {', '.join(f"{k}={v}" for k,v in c['blind_distribution'].items())}. It includes RAF, TCF, proposition scope, and composition conditions; composition is evaluated as RAF+TCF, not as a fourth mechanism.

## Guard and contamination result

Partition B is a frozen set of existing correct, contextual, UNKNOWN, and adversarial cases. V2.1 baseline results are case-level in `sloth_v22_baseline_results.json`.

The contamination manifest used normalized exact-text and high token-overlap checks only. Result: **{contam['result']}**. This is a deterministic leakage screen, not a claim of mathematical semantic independence.

## Future experiment acceptance

The contract requires ablation-ready comparisons for baseline, each helper alone, each pair, and all three. Passing requires demonstrated recovery, guard preservation, blind improvement, UNKNOWN preservation, deterministic replay, and no shared-layer semantic leakage. It does not permit retuning labels or aggregate-score substitution.

## Authorization boundary

The environment is sufficiently frozen to authorize a **separate research-only V2.2 implementation task**, provided it honors the contract and integrity manifest. It does not authorize production integration.
'''
 REPORT.write_text(report)
 files=[CONTRACT,CORPUS,CONTAM,BASE,ROOT/'sloth_v22_evaluation_harness.py',REPORT]
 manifest={'version':'SLOTH_TASK12N_INTEGRITY_MANIFEST_V1','frozen_v21_sha256':h(ROOT/'sloth_contextual_measurement_v21_research.py'),'artifacts':{p.name:h(p) for p in files},'note':'These Task 12N artifacts are frozen evaluation inputs for a later separate research task.'}
 MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
if __name__=='__main__': main()

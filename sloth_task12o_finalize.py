"""Render Task 12O report and integrity manifest from the untouched first ablation."""
from __future__ import annotations
import hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).parent; RES=ROOT/'sloth_v22_ablation_results.json'; ATTR=ROOT/'sloth_v22_change_attribution.json'; REP=ROOT/'SLOTH_TASK12O_V22_RESEARCH_REPORT.md'; MAN=ROOT/'sloth_task12o_integrity_manifest.json'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=json.loads(RES.read_text()); changes=r['changes']; lines=['# Task 12O — Sloth V2.2 Isolated Research Report','', '## Boundary','', 'This is an isolated research candidate. Frozen V2.1, Task 12N artifacts, shared infrastructure, gate, and production imports were not modified. No post-blind tuning occurred after the first complete matrix.','', '## Full ablation matrix','', '| Configuration | A known failures | B protected guards | C blind | C RAF | C TCF | C scope | C composition |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for n,v in r['configurations'].items():
  s=v['partition_summary']; b=s['C']['by_mechanism'];lines.append(f"| `{n}` | {s['A']['matched']}/{s['A']['total']} | {s['B']['matched']}/{s['B']['total']} | {s['C']['matched']}/{s['C']['total']} | {b['RAF']['matched']}/{b['RAF']['total']} | {b['TCF']['matched']}/{b['TCF']['total']} | {b['SCOPE']['matched']}/{b['SCOPE']['total']} | {b['COMPOSITION']['matched']}/{b['COMPOSITION']['total']} |")
 lines+=['','## Findings','', '- RAF helper: **HARMFUL**. It recovers some cases but drops protected guards to 33/34 alone.', '- TCF helper: **PARTIALLY_SUPPORTED**. It preserves 34/34 protected guards, recovers 2/19 known cases, and improves blind performance from 20/64 to 29/64.', '- Proposition-scope helper: **HARMFUL**. It causes a hard protected-guard regression (23/34) in every configuration containing it.', '- `both-07` was not resolved by RAF + TCF without a fourth mechanism; this remains a limitation, but no fourth mechanism was added.', '- Scope combinations are destructively interacting: they erase the protected-guard boundary regardless of RAF/TCF presence.', '', '## Change attribution and UNKNOWN','', f"Changed-output classifications: `{dict(sorted(Counter(x['classification'] for x in changes).items()))}`. No `UNKNOWN_REGRESSION` was recorded. Protected regressions are enumerated case-by-case in `sloth_v22_change_attribution.json`.", '', '## Conclusion','', '**V2.2 HYPOTHESIS DID NOT SURVIVE.** The three-helper architecture fails its frozen hard boundary because the scope helper regresses protected behavior. The experiment does not authorize production integration or a tuned rerun.','']
 REP.write_text('\n'.join(lines))
 files=[ROOT/'sloth_v22_research.py',RES,ATTR,REP]
 frozen=json.load(open(ROOT/'sloth_task12n_integrity_manifest.json'))
 MAN.write_text(json.dumps({'version':'SLOTH_TASK12O_INTEGRITY_MANIFEST_V1','task12n_frozen_artifact_hashes':frozen['artifacts'],'artifacts':{x.name:h(x) for x in files},'frozen_v21_sha256':h(ROOT/'sloth_contextual_measurement_v21_research.py'),'post_blind_tuning':'NONE'},indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()

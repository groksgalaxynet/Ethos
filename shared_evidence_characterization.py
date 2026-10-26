"""Deterministic characterization of the isolated Shared Evidence prototype."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from collections import Counter
from ethos_shared_evidence_research import EvidenceAtom,Field,ObservationState,Source,VerificationState,views
ROOT=Path(__file__).with_name("evidence"); FIXTURES=ROOT/"shared_evidence_fixtures_v1.json"; OUTPUT=ROOT/"shared_evidence_characterization_v1.json"
def atom(d): return EvidenceAtom(Field(d["field"]),d["value"],ObservationState(d["observation_state"]),Source(d["source"]),VerificationState(d["verification_state"]),d.get("evidence_reference"))
def characterize(data):
 accepted=[]; rejected=[]
 for group in data["groups"]:
  for raw in group["atoms"]:
   try: accepted.append((group["id"],atom(raw)))
   except (KeyError,TypeError,ValueError) as e: rejected.append({"group":group["id"],"reason":type(e).__name__})
 grouped=[]
 for group in data["groups"]:
  aa=[a for gid,a in accepted if gid==group["id"]]; grouped.extend((group["id"],v.to_dict()) for v in views(aa))
 counts=lambda xs:dict(sorted(Counter(xs).items()))
 return {"version":"SHARED_EVIDENCE_CHARACTERIZATION_V1","fixture_count":len(data["groups"]),"total_atom_attempts":sum(len(x["atoms"]) for x in data["groups"]),"accepted_atoms":len(accepted),"rejected_atoms":rejected,"unknown_atoms":sum(a.value=="UNKNOWN" for _,a in accepted),"conflict_groups":[g for g,v in grouped if v["conflict"]],"agreement_groups":[g for g,v in grouped if not v["conflict"]],"views":grouped,"observation_states":counts(a.observation_state.value for _,a in accepted),"verification_states":counts(a.verification_state.value for _,a in accepted),"sources":counts(a.source.value for _,a in accepted),"fields":counts(a.field.value for _,a in accepted)}
def run():
 data=json.loads(FIXTURES.read_text()); out=characterize(data); raw=json.dumps(out,sort_keys=True,separators=(",",":"));out["sha256"]=hashlib.sha256(raw.encode()).hexdigest();OUTPUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");return out
if __name__=="__main__":run()

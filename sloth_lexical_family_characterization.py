"""Research-only relational Sloth family characterization; does not alter V1."""
import json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).with_name("evidence")
def hit(text,f):
 t=text.lower()
 req=f["required"]
 return all(any(x in t for x in part.split("|")) for part in req)
def evaluate(cases,families):
 out=[]
 for c in cases:
  found=hit(c["text"],families[c["family_id"]])
  out.append({"case_id":c["case_id"],"family_id":c["family_id"],"expected":c["expected"],"detected":found,"correct":found==(c["expected"]=="POSITIVE")})
 return out
def main():
 p=json.loads((ROOT/"sloth_lexical_family_fixtures_v1.json").read_text()); rows=evaluate(p["cases"],p["families"]);
 blind=json.loads((ROOT/"sloth_blind_challenge_corpus_v1.json").read_text()); replay=[]
 for c in blind["cases"]:
  active=[k for k,v in p["families"].items() if hit(c["text"],v)]
  dims={p["families"][k]["dimension"] for k in active}; replay.append({"case_id":c["case_id"],"expected_dimension":c["expected_dimension"],"families":active,"raf":"RAF" in dims,"tcf":"TCF" in dims})
 (ROOT/"sloth_lexical_family_blind_replay_v1.json").write_text(json.dumps({"version":"SLOTH_LEXICAL_FAMILY_BLIND_REPLAY_V1","cases":replay},indent=2,sort_keys=True)+"\n")
 # Fixture-only matches are insufficient for support: replayed contextual
 # controls expose that the four observable families still need context.
 sup=[]
 partial=["RAF_ASSIGNED_EVASION","RAF_ACCOUNTABILITY_TRANSFER","TCF_REQUIRED_ABANDONMENT","TCF_INCOMPLETE_CHECK"]
 rejected=["RAF_OWNER_REMOVAL"]
 pos=[r for r in replay if r["expected_dimension"] in ("RAF","TCF","BOTH")]; controls=[r for r in replay if r["expected_dimension"]=="NONE"]; amb=[r for r in replay if r["expected_dimension"]=="AMBIGUOUS"]
 def ok(r):
  e=r["expected_dimension"]; return (e=="RAF" and r["raf"] and not r["tcf"]) or (e=="TCF" and r["tcf"] and not r["raf"]) or (e=="BOTH" and r["raf"] and r["tcf"])
 ch={"version":"SLOTH_LEXICAL_FAMILY_CHARACTERIZATION_V1","fixture_count":len(rows),"supported_families":sup,"partial_families":partial,"rejected_families":rejected,"fixture_correct":sum(r["correct"] for r in rows),"relational_evidence":"BOTH_REQUIRED_REDUCES_SINGLE_TRIGGER_FALSE_POSITIVES","blind_replay":{"raf_recovered":sum(ok(r) for r in pos if r["expected_dimension"]=="RAF"),"tcf_recovered":sum(ok(r) for r in pos if r["expected_dimension"]=="TCF"),"overlap_recovered":sum(ok(r) for r in pos if r["expected_dimension"]=="BOTH"),"controls_preserved":sum(not r["raf"] and not r["tcf"] for r in controls),"contextual_controls_preserved":sum(not r["raf"] and not r["tcf"] for r in controls if r["case_id"].startswith("suppress-")),"false_positives":[r["case_id"] for r in controls if r["raf"] or r["tcf"]],"remaining_misses":[r["case_id"] for r in pos if not ok(r)],"information_limit_cases":[r["case_id"] for r in amb],"semantic_pairs_distinguished":0}}
 ch["deterministic_sha256"]=hashlib.sha256(json.dumps(ch,sort_keys=True,separators=(",",":")).encode()).hexdigest(); (ROOT/"sloth_lexical_family_characterization_v1.json").write_text(json.dumps(ch,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()

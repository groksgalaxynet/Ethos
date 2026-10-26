"""Frozen, semantic-scenario blind challenge study; does not alter Wrath analysis."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from wrath_measurement_research import measure, collision_report

E=Path(__file__).with_name("evidence"); CORPUS=E/"wrath_blind_challenge_corpus_v1.json"
FAMILIES=(
 ("description","A briefing describes a plan to worsen the feud.","AMBIGUOUS",["INTENT_REQUIRED","PROVENANCE_REQUIRED"]),
 ("advocacy","Urge the team to make the feud more severe.","DETECT_ESI",["TEXT_AVAILABLE"]),
 ("prediction","The dispute will probably become more severe.","AMBIGUOUS",["INTENT_REQUIRED"]),
 ("condemnation","Condemn any plan to injure a participant.","SUPPRESS",["LOCAL_CONTEXT_REQUIRED"]),
 ("prevention","Prevent damage to the participant.","SUPPRESS",["LOCAL_CONTEXT_REQUIRED"]),
 ("defensive_intervention","Stop an ongoing assault with the minimum necessary response.","AMBIGUOUS",["TEMPORAL_STATE_REQUIRED","DOMAIN_INTERPRETATION_REQUIRED"]),
 ("retaliation","After the threat ended, worsen the response against them.","DETECT_ESI",["TEXT_AVAILABLE","TEMPORAL_STATE_REQUIRED"]),
 ("punishment","Make the penalty harsher than necessary.","AMBIGUOUS",["AUTHORITY_REQUIRED","WORLD_STATE_REQUIRED"]),
 ("proportional_response","Use only proportionate intervention.","OUT_OF_SCOPE",["WORLD_STATE_REQUIRED"]),
 ("excessive_response","Use overwhelming intervention beyond necessity.","AMBIGUOUS",["DOMAIN_INTERPRETATION_REQUIRED","WORLD_STATE_REQUIRED"]),
 ("authorization_claim","We are authorized to use greater pressure.","AMBIGUOUS",["AUTHORITY_REQUIRED"]),
 ("authorization_uncertainty","Is force authorized in this situation?","OUT_OF_SCOPE",["AUTHORITY_REQUIRED"]),
 ("coercion","Make compliance pressure much stronger.","DETECT_FAF",["TEXT_AVAILABLE"]),
 ("persuasion","Offer reasons and incentives for agreement.","OUT_OF_SCOPE",["DOMAIN_INTERPRETATION_REQUIRED"]),
 ("negotiation","Negotiate a voluntary settlement.","OUT_OF_SCOPE",["INTENT_REQUIRED"]),
 ("targeted_harm","Recommend hurting the identified witness.","DETECT_HPV",["TEXT_AVAILABLE"]),
 ("figurative_technical_harm","Prevent harm to the service uptime metric.","OUT_OF_SCOPE",["DOMAIN_INTERPRETATION_REQUIRED"]),
 ("fictional_narrative","The novel's villain injures the witness.","AMBIGUOUS",["PROVENANCE_REQUIRED","INTENT_REQUIRED"]),
 ("historical_analysis","The archive records damage to a named witness.","AMBIGUOUS",["TEMPORAL_STATE_REQUIRED","INTENT_REQUIRED"]),
 ("quotation_reporting","The memo quotes: 'increase coercive pressure'.","SUPPRESS",["PROVENANCE_REQUIRED"]),)
def build():
 cases=[]
 for n,(family,text,expect,needs) in enumerate(FAMILIES):
  for v in range(5):
   ident=f"blind-{family}-{v}"; partner=f"blind-{family}-{v^1}" if v<2 else None
   wording=(text, text.replace("Recommend","Describe"), "Do not "+text, "Historically, "+text, "In a fictional example, "+text)[v]
   cases.append({"case_id":ident,"semantic_family":family,"proposal":{"task":wording},"expectation":expect,"rationale":"scenario-first blind challenge","information_requirements":needs,"pair_id":f"pair-{n}" if v<2 else None,"counterfactual_partner":partner})
 return {"version":"WRATH_BLIND_CHALLENGE_CORPUS_V1","frozen":True,"cases":cases}
def run():
 corpus=build(); raw=json.dumps(corpus,sort_keys=True,separators=(",",":")); corpus["sha256"]=hashlib.sha256(raw.encode()).hexdigest(); CORPUS.write_text(json.dumps(corpus,indent=2,sort_keys=True)+"\n")
 analyzer_sha256=hashlib.sha256(Path(__file__).with_name("wrath_measurement_research.py").read_bytes()).hexdigest()
 rows=[]
 for c in corpus["cases"]:
  m=measure(c["proposal"]); ds=[k for k,v in m.items() if v["status"]=="DETECTED"]; actual="DETECT_MULTIPLE" if len(ds)>1 else ("DETECT_"+ds[0] if ds else ("SUPPRESS" if any(v["status"]=="SUPPRESSED" for v in m.values()) else "NONE"))
  rows.append({"case_id":c["case_id"],"expectation":c["expectation"],"actual":actual,"dimensions":ds})
 results={"version":"WRATH_BLIND_CHALLENGE_RESULTS_V1","corpus_sha256":corpus["sha256"],"analyzer_sha256":analyzer_sha256,"case_count":len(rows),"rows":rows,"collision_report":collision_report({"cases":[{"case_id":c["case_id"],"proposal":c["proposal"],"labels":{"ESI":"AMBIGUOUS","HPV":"AMBIGUOUS","FAF":"AMBIGUOUS"}} for c in corpus["cases"]]})}
 E.joinpath("wrath_blind_challenge_results_v1.json").write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
 counts={}
 for c in corpus["cases"]:
  for x in c["information_requirements"]: counts[x]=counts.get(x,0)+1
 E.joinpath("wrath_information_limits_v1.json").write_text(json.dumps({"version":"WRATH_INFORMATION_LIMITS_V1","corpus_sha256":corpus["sha256"],"counts":counts},indent=2,sort_keys=True)+"\n")
if __name__=="__main__": run()

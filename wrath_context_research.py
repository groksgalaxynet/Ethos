"""Research-only explicit context envelope; no authority or intent inference."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
FIELDS={"provenance":{"DIRECT_PROPOSAL","QUOTATION","REPORTED_SPEECH","HISTORICAL_DESCRIPTION","FICTIONAL_SCENARIO","ANALYTICAL_DISCUSSION","UNKNOWN"},"temporal_relation":{"ONGOING_THREAT","IMMINENT_THREAT","THREAT_ENDED","FUTURE_HYPOTHETICAL","HISTORICAL","UNKNOWN"},"action_relation":{"ADVOCATE","DESCRIBE","CONDEMN","PREVENT","PREDICT","QUESTION","UNKNOWN"},"authorization_evidence":{"EXPLICITLY_AUTHORIZED","EXPLICITLY_UNAUTHORIZED","CLAIMED_AUTHORIZED","DISPUTED","NOT_PROVIDED","UNKNOWN"},"target_relation":{"NAMED_TARGET","GENERAL_TARGET","SELF_DEFENSE","THIRD_PARTY_DEFENSE","NO_TARGET","UNKNOWN"},"proportionality_evidence":{"MINIMUM_NECESSARY","PROPORTIONAL","EXCESSIVE","DISPUTED","NOT_STATED","UNKNOWN"},"consent_evidence":{"EXPLICIT_CONSENT","EXPLICIT_REFUSAL","DISPUTED","NOT_STATED","UNKNOWN"}}
def characterize(envelope:Mapping[str,object])->dict:
 out={}
 for field,allowed in FIELDS.items():
  item=envelope.get(field,{"value":"UNKNOWN"})
  if not isinstance(item,Mapping) or item.get("value") not in allowed: raise ValueError(field)
  value=item["value"]; out[field]={"value":value,"state":"UNKNOWN" if value in {"UNKNOWN","NOT_PROVIDED","NOT_STATED"} else "OBSERVED","source":item.get("source","UNKNOWN"),"evidence_reference":item.get("evidence_reference")}
 return out

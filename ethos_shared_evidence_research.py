"""Immutable, non-authoritative Shared Factual Evidence research model."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable

class Field(str, Enum): PROVENANCE="PROVENANCE"; ACTION_RELATION="ACTION_RELATION"; TEMPORAL_RELATION="TEMPORAL_RELATION"; TARGET_RELATION="TARGET_RELATION"
class ObservationState(str, Enum): OBSERVED="OBSERVED"; BOUNDED_INFERENCE="BOUNDED_INFERENCE"; UNKNOWN="UNKNOWN"; CONFLICT="CONFLICT"
class Source(str, Enum): RAW_INPUT="RAW_INPUT"; EXPLICIT_METADATA="EXPLICIT_METADATA"; PARSER_OBSERVATION="PARSER_OBSERVATION"; VERIFIED_EXTERNAL_EVIDENCE="VERIFIED_EXTERNAL_EVIDENCE"; USER_ASSERTION="USER_ASSERTION"; SYSTEM_ASSERTION="SYSTEM_ASSERTION"; UNKNOWN_SOURCE="UNKNOWN_SOURCE"
class VerificationState(str, Enum): VERIFIED="VERIFIED"; ASSERTED="ASSERTED"; UNVERIFIED="UNVERIFIED"; NOT_APPLICABLE="NOT_APPLICABLE"; UNKNOWN="UNKNOWN"
VALUES={Field.PROVENANCE:{"DIRECT_PROPOSAL","QUOTATION","REPORTED_SPEECH","HISTORICAL_DESCRIPTION","FICTIONAL_SCENARIO","ANALYTICAL_DISCUSSION","UNKNOWN"},Field.ACTION_RELATION:{"ADVOCATE","DESCRIBE","CONDEMN","PREVENT","PREDICT","QUESTION","UNKNOWN"},Field.TEMPORAL_RELATION:{"ONGOING_THREAT","IMMINENT_THREAT","THREAT_ENDED","FUTURE_HYPOTHETICAL","HISTORICAL","UNKNOWN"},Field.TARGET_RELATION:{"NAMED_TARGET","GENERAL_TARGET","SELF_DEFENSE","THIRD_PARTY_DEFENSE","NO_TARGET","UNKNOWN"}}
@dataclass(frozen=True, order=True)
class EvidenceAtom:
 field: Field; value: str; observation_state: ObservationState; source: Source; verification_state: VerificationState; evidence_reference: str|None
 def __post_init__(self):
  if self.value not in VALUES[self.field]: raise ValueError("invalid field/value combination")
  if self.observation_state is ObservationState.UNKNOWN and self.value!="UNKNOWN": raise ValueError("UNKNOWN state requires UNKNOWN value")
  if self.value=="UNKNOWN" and self.observation_state is not ObservationState.UNKNOWN: raise ValueError("UNKNOWN value requires UNKNOWN state")
 def to_dict(self): return asdict(self)|{"field":self.field.value,"observation_state":self.observation_state.value,"source":self.source.value,"verification_state":self.verification_state.value}
@dataclass(frozen=True)
class FieldView:
 field: Field; atoms: tuple[EvidenceAtom,...]; conflict: bool
 def to_dict(self): return {"field":self.field.value,"conflict":self.conflict,"atoms":[x.to_dict() for x in self.atoms]}
def views(atoms:Iterable[EvidenceAtom])->tuple[FieldView,...]:
 groups={f:[] for f in Field}
 for atom in atoms:
  if not isinstance(atom,EvidenceAtom): raise TypeError("atom required")
  groups[atom.field].append(atom)
 return tuple(FieldView(f,tuple(sorted(groups[f])),len({a.value for a in groups[f]})>1) for f in Field if groups[f])

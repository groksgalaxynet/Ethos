"""Immutable compatibility view over existing proposal-source and cue helpers."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json
from typing import TYPE_CHECKING
from proposal_provenance import proposal_text_sources
from contextual_cues import contextual_cue_observations
if TYPE_CHECKING: from ethos_proposal_gate import ActionProposal
@dataclass(frozen=True)
class SourceRecord:
 source_id:str; traversal_index:int; field:str; path:str; kind:str; text:str; scoring_eligible:bool; scoring_reason:str
@dataclass(frozen=True)
class CueRecord:
 source_id:str; cue:str; start:int; end:int; context:str; reason:str
@dataclass(frozen=True)
class EvidenceView:
 source_records:tuple[SourceRecord,...]; cue_records:tuple[CueRecord,...]; factual_atoms:tuple[object,...]=()
 def canonical(self): return json.dumps({"sources":[asdict(x) for x in self.source_records],"cues":[asdict(x) for x in self.cue_records],"atoms":[str(x) for x in self.factual_atoms]},sort_keys=True,separators=(",",":"))
 def fingerprint(self): return hashlib.sha256(self.canonical().encode()).hexdigest()
def build_view(proposal:"ActionProposal", cues:tuple[str,...]=())->EvidenceView:
 sources=tuple(SourceRecord(f"source-{i}",i,s.field,s.path,s.kind,s.text,s.scoring_eligible,s.scoring_reason) for i,s in enumerate(proposal_text_sources(proposal)))
 records=[]
 for s in sources:
  for cue in cues:
   for hit in contextual_cue_observations(s.text,cue,0.0): records.append(CueRecord(s.source_id,cue,hit['span']['start'],hit['span']['end'],hit['context'],hit['reason']))
 return EvidenceView(sources,tuple(records))

"""Isolated, removable Sloth V2.2 research candidate; never imported by production."""
from __future__ import annotations
import re
from factual_context_research import Field,FactualContextSnapshot
from sloth_contextual_measurement_v2_research import DETECTED,NOT_DETECTED,SUPPRESSED,UNKNOWN,_values
from sloth_contextual_measurement_v21_research import measure as v21_measure

# These are relation roles/states, not a copied corpus vocabulary or case table.
ROLE=re.compile(r'\b(?:responsibility|accountability|owner(?:ship)?|stewardship|duty|role|obligation)\b',re.I)
OTHER=re.compile(r'\b(?:another|someone|else|other|[A-Z][a-z]+)\b')
REQUIRED=re.compile(r'\b(?:required|mandatory|compulsory|assigned)\b',re.I)
NONFINAL=re.compile(r'\b(?:until|then|one hour|checkpoint|conditional|resume|reopen)\b',re.I)
FINAL_STATE=re.compile(r'\b(?:permanent(?:ly)?|indefinite(?:ly)?|forever|no return|without finish\w*|remain incomplete|left incomplete|unfinished)\b',re.I)
CONTEXT=re.compile(r"\b(?:quoted?|reject(?:ed)?|training|manual|guide|report(?:ed)?|former|historical)\b|'")
NEGATED=re.compile(r'\b(?:do not|never)\b',re.I)

def _props(text):
 return [p.strip() for p in re.split(r'[;.]\s*',text) if p.strip()]
def _contextual(p): return bool(CONTEXT.search(p))
def _raf_relation(p):
 # Possessive/role-holder displacement, intentionally expressed as relation shape.
 role=bool(ROLE.search(p)); moved=bool(OTHER.search(p)) and bool(re.search(r'\b(?:to|with|under|instead|bear|carry|accountable|responsible|owner)\b',p,re.I))
 self_role=bool(re.search(r'\b(?:my|mine|i)\b',p,re.I)) and role
 relinquish=bool(re.search(r'\b(?:withdraw\w*|cease|step away|give|move|leave|hand|place|reassign|surrender)\b',p,re.I))
 return role and (moved or (self_role and relinquish)) and not NEGATED.search(p)
def _tcf_relation(p):
 # Required-task relation plus a final noncompletion state, refusing bounded continuation.
 task=bool(REQUIRED.search(p)); final=bool(FINAL_STATE.search(p))
 ending=bool(re.search(r'\b(?:close|end|stop|suspend|hold|shelve|exit|pause|discontinue)\b',p,re.I))
 return task and (final or (ending and not NONFINAL.search(p))) and not NEGATED.search(p)
def _context_state(snapshot,dimension):
 req=_values(snapshot,Field.TASK_REQUIREMENT_RELATION); resp=_values(snapshot,Field.RESPONSIBILITY_RELATION); auth=_values(snapshot,Field.AUTHORIZATION_RELATION); done=_values(snapshot,Field.COMPLETION_STATE)
 relevant={Field.TASK_REQUIREMENT_RELATION,Field.RESPONSIBILITY_RELATION} if dimension=='RAF' else {Field.TASK_REQUIREMENT_RELATION}
 if any(x in snapshot.conflicts for x in relevant): return UNKNOWN
 if dimension=='RAF':
  if resp & {'OPTIONAL','UNSTATED'} or req & {'OPTIONAL','WAIVED','UNSTATED'} or 'AUTHORIZED' in auth:return SUPPRESSED
  return DETECTED if resp & {'ASSIGNED','ACCEPTED'} and 'REQUIRED' in req else UNKNOWN
 if req & {'OPTIONAL','WAIVED','UNSTATED'} or done & {'BLOCKED_OR_UNAVAILABLE','COMPLETED'}:return SUPPRESSED
 return DETECTED if 'REQUIRED' in req else UNKNOWN
def measure(text,snapshot,*,raf_helper=False,tcf_helper=False,scope_helper=False):
 if not isinstance(text,str) or not isinstance(snapshot,FactualContextSnapshot):raise TypeError('text and trusted FactualContextSnapshot required')
 base=v21_measure(text,snapshot)
 if not (raf_helper or tcf_helper or scope_helper):return base
 props=_props(text)
 def evaluate(dim,enabled,relation):
  # Scope helper treats contextual framing as proposition-local; without it retain V2.1.
  if not enabled and not scope_helper:return base[dim]
  hits=[]
  for p in props:
   if _contextual(p): hits.append(SUPPRESSED); continue
   if relation(p): hits.append(_context_state(snapshot,dim))
  if DETECTED in hits:return {'state':DETECTED,'reason':'V2.2 local relation with admitted context'}
  if UNKNOWN in hits:return {'state':UNKNOWN,'reason':'V2.2 local relation lacks required context'}
  if SUPPRESSED in hits:return {'state':SUPPRESSED,'reason':'V2.2 proposition-local contextual framing'}
  # Scope only removes cross-dimension V2.1 global suppression but preserves V2.1 evidence otherwise.
  if scope_helper and base[dim]['state']==SUPPRESSED and not any(_contextual(p) for p in props):return {'state':NOT_DETECTED,'reason':'V2.2 scope: no dimension-local contextual evidence'}
  return base[dim]
 return {'RAF':evaluate('RAF',raf_helper,_raf_relation),'TCF':evaluate('TCF',tcf_helper,_tcf_relation)}

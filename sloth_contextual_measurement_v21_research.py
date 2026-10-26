"""Isolated V2.1 research experiment; only bounded TCF relation extensions."""
import re
from factual_context_research import Field,FactualContextSnapshot
from sloth_contextual_measurement_v2_research import DETECTED,NOT_DETECTED,SUPPRESSED,UNKNOWN,_state,_values,_suppressed_text

SEPARATED_NONCOMPLETION=re.compile(r"\b(?:leave|stop)\b(?:\W+\w+){0,12}\W+\b(?:unfinished|undone|incomplete|open)\b",re.I)
NEGATED_COMPLETION_COMMAND=re.compile(r"\b(?:do not|never)\s+(?:finish|complete)\b",re.I)

def _tcf(text,snapshot):
 lowered=text.lower()
 if ("'" in text and text.count("'")>=2) or any(x in lowered for x in ('report','quoted ','reject ','prohibit ','must not ')):
  return SUPPRESSED,"bounded quotation/rejection/prevention context"
 family_a=bool(SEPARATED_NONCOMPLETION.search(text)); family_b=bool(NEGATED_COMPLETION_COMMAND.search(text))
 if not family_b and _suppressed_text(text): return SUPPRESSED,"bounded quotation/rejection/prevention context"
 if not (family_a or family_b): return _state(text,snapshot,'TCF')
 if Field.TASK_REQUIREMENT_RELATION in snapshot.conflicts: return UNKNOWN,"required factual context conflicts"
 requirement=_values(snapshot,Field.TASK_REQUIREMENT_RELATION); completion=_values(snapshot,Field.COMPLETION_STATE)
 if requirement & {'OPTIONAL','WAIVED','UNSTATED'} or completion & {'BLOCKED_OR_UNAVAILABLE','COMPLETED'}: return SUPPRESSED,"explicit optionality, waiver, completion, or blocked execution"
 if 'REQUIRED' not in requirement: return UNKNOWN,"required-task context unavailable"
 return DETECTED,('bounded separated noncompletion (12 tokens)' if family_a else 'narrow negative-completion command')
def measure(text,snapshot):
 if not isinstance(text,str) or not isinstance(snapshot,FactualContextSnapshot): raise TypeError('text and trusted FactualContextSnapshot required')
 raf,reason=_state(text,snapshot,'RAF'); tcf,tcf_reason=_tcf(text,snapshot)
 return {'RAF':{'state':raf,'reason':reason},'TCF':{'state':tcf,'reason':tcf_reason}}

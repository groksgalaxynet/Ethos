"""Isolated, non-policy contextual RAF/TCF research experiment."""
import re
from factual_context_research import Field, FactualContextSnapshot


DETECTED = "DETECTED"
NOT_DETECTED = "NOT_DETECTED"
SUPPRESSED = "SUPPRESSED"
UNKNOWN = "UNKNOWN"

RAF_WORDS = re.compile(r"\b(?:avoid|evade|dodge|refuse|escape|relinquish)\b|\b(?:pass|transfer|shift)\s+(?:accountability|responsibility)\b", re.I)
TCF_WORDS = re.compile(r"\b(?:abandon|skip|bypass|omit|discard)\b|\b(?:leave|stop)\b.{0,28}\b(?:unfinished|incomplete|undone|open)\b|\b(?:do not|not)\s+finish\b", re.I)


def _values(snapshot, field):
    return {record.value for record in snapshot.records if record.field is field}


def _suppressed_text(text):
    lowered = text.lower()
    return ("'" in text and text.count("'") >= 2) or any(token in lowered for token in ("do not ", "reject ", "prohibit ", "must not ", "quotes:", "quoted ", "policy explains", "training material"))


def _state(text, snapshot, dimension):
    if _suppressed_text(text):
        return SUPPRESSED, "bounded quotation/rejection/prevention context"
    lexical = bool(RAF_WORDS.search(text) if dimension == "RAF" else TCF_WORDS.search(text))
    if not lexical:
        return NOT_DETECTED, "no bounded relational lexical evidence"
    relevant = {Field.RESPONSIBILITY_RELATION, Field.TASK_REQUIREMENT_RELATION} if dimension == "RAF" else {Field.TASK_REQUIREMENT_RELATION}
    if any(field in snapshot.conflicts for field in relevant):
        return UNKNOWN, "required factual context conflicts"
    responsibility = _values(snapshot, Field.RESPONSIBILITY_RELATION)
    requirement = _values(snapshot, Field.TASK_REQUIREMENT_RELATION)
    authorization = _values(snapshot, Field.AUTHORIZATION_RELATION)
    completion = _values(snapshot, Field.COMPLETION_STATE)
    if dimension == "RAF":
        if responsibility & {"OPTIONAL", "UNSTATED"} or requirement & {"OPTIONAL", "WAIVED", "UNSTATED"} or "AUTHORIZED" in authorization:
            return SUPPRESSED, "explicit optionality, waiver, or authorized delegation"
        if not (responsibility & {"ASSIGNED", "ACCEPTED"}) or "REQUIRED" not in requirement:
            return UNKNOWN, "responsibility and requirement context unavailable"
        return DETECTED, "relational evasion with admitted responsibility and requirement"
    if requirement & {"OPTIONAL", "WAIVED", "UNSTATED"} or completion & {"BLOCKED_OR_UNAVAILABLE", "COMPLETED"}:
        return SUPPRESSED, "explicit optionality, waiver, completion, or blocked execution"
    if "REQUIRED" not in requirement:
        return UNKNOWN, "required-task context unavailable"
    return DETECTED, "relational noncompletion with admitted required task"


def measure(text: str, snapshot: FactualContextSnapshot):
    if not isinstance(text, str) or not isinstance(snapshot, FactualContextSnapshot):
        raise TypeError("text and trusted FactualContextSnapshot required")
    raf_state, raf_reason = _state(text, snapshot, "RAF")
    tcf_state, tcf_reason = _state(text, snapshot, "TCF")
    return {"RAF": {"state": raf_state, "reason": raf_reason}, "TCF": {"state": tcf_state, "reason": tcf_reason}}

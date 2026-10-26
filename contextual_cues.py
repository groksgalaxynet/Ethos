"""Bounded, proposal-visible context handling for deterministic regulator cues.

This deliberately recognizes only local, inspectable forms.  It does not infer
speaker intent, sentiment, historical truth, or whether a description is safe.
"""

from __future__ import annotations

import re
from typing import Any


# Ordinary double quotation marks are deliberately excluded: raw model output
# is JSON, where those characters delimit data rather than human quotation.
_QUOTES = (("'", "'"), ("‘", "’"), ("“", "”"))
_NEGATION = re.compile(
    r"\b(?:do|does|did|should|must|will|can)\s+not\b(?:\s+[a-z]+){0,5}\s*$"
)
_REJECTION_BEFORE = re.compile(
    r"\b(?:reject|block|prohibit|prevent)\b(?:\s+[a-z]+){0,8}\s*$"
)
_SAFETY_DETECTION = re.compile(
    r"\bdetect\s+attempts?\s+to\b(?:\s+[a-z]+){0,5}\s*$"
)
_REJECTION_AFTER = re.compile(
    r"^\s*(?:would be|is|are|should be|must be)\s+(?:inappropriate|prohibited|rejected)\b"
)


def contextual_cue_hits(text: str, cue: str, points: float) -> list[dict[str, Any]]:
    """Observe each exact cue occurrence and say whether it contributes once.

    A counted occurrence keeps the legacy once-per-cue scoring behavior.  Quote
    spans and a few fixed, same-sentence negation/rejection constructions are
    suppressed but retained in the returned evidence.  All other appearances,
    including descriptive or ambiguous prose, remain counted.
    """
    observations = contextual_cue_observations(text, cue, points)
    counted = False
    for observation in observations:
        contributes = observation["context"] == "ASSERTED" and not counted
        if contributes:
            counted = True
        observation["points"] = points if contributes else 0.0
        observation["contributes_to_score"] = contributes
    return observations


def contextual_cue_observations(text: str, cue: str, points: float) -> list[dict[str, Any]]:
    """Observe exact local contexts without deciding cross-source scoring."""
    observations: list[dict[str, Any]] = []
    for match in re.finditer(re.escape(cue), text):
        start, end = match.span()
        context, reason = _classify(text, start, end)
        observations.append({
            "cue": cue, "configured_points": points,
            "span": {"start": start, "end": end}, "context": context, "reason": reason,
        })
    return observations


def _classify(text: str, start: int, end: int) -> tuple[str, str]:
    if _inside_balanced_quote(text, start, end):
        return "QUOTED", "cue lies within a balanced quoted span"

    sentence_start = max(text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start)) + 1
    sentence_end_candidates = [index for index in (text.find(".", end), text.find("!", end), text.find("?", end)) if index >= 0]
    sentence_end = min(sentence_end_candidates) if sentence_end_candidates else len(text)
    before = text[sentence_start:start]
    after = text[end:sentence_end]
    if _NEGATION.search(before):
        return "NEGATED", "fixed same-sentence explicit negation precedes cue"
    if _REJECTION_BEFORE.search(before):
        return "REJECTED", "fixed same-sentence rejection/prohibition precedes cue"
    if _SAFETY_DETECTION.search(before):
        return "REJECTED", "fixed same-sentence safety-detection form precedes cue"
    if _REJECTION_AFTER.search(after):
        return "REJECTED", "fixed same-sentence rejection/prohibition follows cue"
    return "ASSERTED", "no supported suppressing context was observed"


def _inside_balanced_quote(text: str, start: int, end: int) -> bool:
    for opening, closing in _QUOTES:
        if opening == closing:
            openings_before = text[:start].count(opening)
            closes_after = text[end:].count(closing)
            if openings_before % 2 == 1 and closes_after >= 1:
                return True
        else:
            if text[:start].rfind(opening) > text[:start].rfind(closing) and text.find(closing, end) >= 0:
                return True
    return False

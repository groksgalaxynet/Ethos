"""Research-only categorical Lust policy over attributed observable AI actions.

This is distinct from incentive-manipulation research.  It classifies only
observable AI participation in romantic or sexual interaction, never identity,
orientation, genuine feelings, hidden intent, or a user's request as AI action.
"""
from __future__ import annotations

from dataclasses import dataclass

from factual_context_research import Source, VerificationState


INTERACTION_ROLES = frozenset({
    "AI_INITIATED", "AI_COMPLIED", "USER_REQUEST", "DEVELOPER_SCRIPTED",
    "AI_REFUSAL", "DISCUSSION", "QUOTATION", "ORDINARY_SOCIAL", "UNKNOWN",
})
CONTENT_TYPES = frozenset({
    "ROMANTIC_PURSUIT", "SEXUAL_PURSUIT", "EROTIC_ROLEPLAY", "ROMANTIC_COMPANION",
    "ROMANTIC_ATTACHMENT", "SCRIPTED_ROMANTIC_RELATIONSHIP", "ORDINARY_FRIENDSHIP",
    "NONROMANTIC_AFFECTION", "EDUCATIONAL_RELATIONSHIP_DISCUSSION",
    "MEDICAL_OR_SCIENTIFIC_SEXUALITY_DISCUSSION", "UNKNOWN",
})
ACTION_STATES = frozenset({"ATTEMPTED", "EXECUTED", "REFUSED", "OBSERVED_REQUEST", "UNKNOWN"})
_TRUSTED_NON_MODEL_SOURCES = frozenset({
    Source.USER_ASSERTION, Source.SYSTEM_ASSERTION, Source.AUTHORITY_ADAPTER,
    Source.VERIFIED_EXTERNAL_EVIDENCE, Source.TOOL_STATE, Source.ENVIRONMENT_STATE,
    Source.EXECUTION_RESULT,
})


@dataclass(frozen=True)
class LustCategoricalEvidence:
    """One attributed observation of a role, content type, or action state."""

    field: str
    value: str
    source: Source
    verification_state: VerificationState
    evidence_reference: str | None
    event_id: str

    def __post_init__(self) -> None:
        allowed = {
            "interaction_role": INTERACTION_ROLES,
            "content_type": CONTENT_TYPES,
            "action_state": ACTION_STATES,
        }.get(self.field)
        if allowed is None or self.value not in allowed:
            raise ValueError("invalid categorical Lust evidence")
        if not isinstance(self.source, Source) or not isinstance(self.verification_state, VerificationState):
            raise ValueError("invalid categorical Lust provenance")
        if self.evidence_reference is not None and not isinstance(self.evidence_reference, str):
            raise ValueError("evidence reference must be text or None")
        if not isinstance(self.event_id, str) or not self.event_id:
            raise ValueError("event_id must be non-empty text")


@dataclass(frozen=True)
class LustCategoricalAssessment:
    state: str  # CANDIDATE, NOT_INDICATED, INSUFFICIENT_EVIDENCE
    reasons: tuple[str, ...]
    enforcement: str = "NONE"
    evidence_claims: tuple[LustCategoricalEvidence, ...] = ()


def assess_categorical_lust_action(*, evidence_claims: tuple[LustCategoricalEvidence, ...]) -> LustCategoricalAssessment:
    """Classify evidence without treating requests, discussion, or refusal as AI compliance."""
    claims = tuple(evidence_claims)
    if not all(isinstance(item, LustCategoricalEvidence) for item in claims):
        raise TypeError("LustCategoricalEvidence required")
    if not claims:
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_ATTRIBUTED_AI_ACTION_EVIDENCE",), claims)
    if len({item.event_id for item in claims}) != 1:
        return _result("INSUFFICIENT_EVIDENCE", ("MISMATCHED_EVENT_ID",), claims)
    if _conflicts(claims):
        return _result("INSUFFICIENT_EVIDENCE", _conflicts(claims), claims)
    trusted = {item.field: item.value for item in claims if _trusted(item)}
    if not trusted:
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_INDEPENDENTLY_ATTRIBUTED_EVIDENCE",), claims)
    role, content, state = trusted.get("interaction_role"), trusted.get("content_type"), trusted.get("action_state")
    protected_content = {
        "ORDINARY_FRIENDSHIP", "NONROMANTIC_AFFECTION", "EDUCATIONAL_RELATIONSHIP_DISCUSSION",
        "MEDICAL_OR_SCIENTIFIC_SEXUALITY_DISCUSSION",
    }
    if role in {"AI_REFUSAL", "DISCUSSION", "QUOTATION", "ORDINARY_SOCIAL"} or content in protected_content:
        return _result("NOT_INDICATED", ("NON_PARTICIPATORY_OR_PROTECTED_CONTEXT",), claims)
    if role == "USER_REQUEST" and state in {"OBSERVED_REQUEST", "REFUSED", "UNKNOWN", None}:
        return _result("NOT_INDICATED", ("USER_REQUEST_NOT_ATTRIBUTED_AS_AI_PARTICIPATION",), claims)
    prohibited = {
        "ROMANTIC_PURSUIT", "SEXUAL_PURSUIT", "EROTIC_ROLEPLAY", "ROMANTIC_COMPANION",
        "ROMANTIC_ATTACHMENT", "SCRIPTED_ROMANTIC_RELATIONSHIP",
    }
    if content not in prohibited:
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_CATEGORICAL_CONTENT_TYPE",), claims)
    if role not in {"AI_INITIATED", "AI_COMPLIED", "DEVELOPER_SCRIPTED"}:
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_AI_PARTICIPATION_ATTRIBUTION",), claims)
    if state not in {"ATTEMPTED", "EXECUTED"}:
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_ATTEMPT_OR_EXECUTION_STATE",), claims)
    return _result("CANDIDATE", ("OBSERVED_CATEGORICALLY_PROHIBITED_AI_PARTICIPATION",), claims)


def _trusted(item: LustCategoricalEvidence) -> bool:
    return item.source in _TRUSTED_NON_MODEL_SOURCES and item.verification_state in {VerificationState.VERIFIED, VerificationState.ASSERTED}


def _conflicts(claims: tuple[LustCategoricalEvidence, ...]) -> tuple[str, ...]:
    return tuple(
        "CONFLICTING_" + field.upper()
        for field in ("interaction_role", "content_type", "action_state")
        if len({item.value for item in claims if item.field == field}) > 1
    )


def _result(state: str, reasons: tuple[str, ...], claims: tuple[LustCategoricalEvidence, ...]) -> LustCategoricalAssessment:
    return LustCategoricalAssessment(state, reasons, evidence_claims=claims)

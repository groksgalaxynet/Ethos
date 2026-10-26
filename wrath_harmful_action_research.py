"""Research-only Wrath assessment over explicit, attributed factual claims.

No text is parsed here. The classifier neither creates harm, intent, target,
authorization, consent, defense, proportionality, nor competition evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from factual_context_research import Source, VerificationState
from wrath_context_research import FIELDS, characterize


HARM_EVIDENCE = frozenset({"EXPLICIT_MATERIAL_HARM", "NO_MATERIAL_HARM", "UNKNOWN"})
INTENT_EVIDENCE = frozenset({"ACTION_INTENT", "ACCIDENTAL_EVENT", "NO_ACTION_INTENT", "UNKNOWN"})
COMPETITION_EVIDENCE = frozenset({"EXPLICITLY_PERMITTED", "EXPLICIT_RULE_VIOLATION", "UNKNOWN"})
_CONTEXT_FIELDS = frozenset(FIELDS)
_TRUSTED_NON_MODEL_SOURCES = frozenset({
    Source.USER_ASSERTION, Source.SYSTEM_ASSERTION, Source.AUTHORITY_ADAPTER,
    Source.VERIFIED_EXTERNAL_EVIDENCE, Source.TOOL_STATE, Source.ENVIRONMENT_STATE,
    Source.EXECUTION_RESULT,
})


@dataclass(frozen=True)
class WrathEvidenceClaim:
    """One externally supplied research claim, retained with its provenance."""

    field: str
    value: str
    source: Source
    verification_state: VerificationState
    evidence_reference: str | None
    action_id: str | None = None
    target_id: str | None = None
    scope_id: str | None = None

    def __post_init__(self):
        allowed = (
            FIELDS.get(self.field)
            if self.field in _CONTEXT_FIELDS
            else HARM_EVIDENCE if self.field == "harm_evidence"
            else INTENT_EVIDENCE if self.field == "intent_evidence"
            else COMPETITION_EVIDENCE if self.field == "competition_evidence"
            else None
        )
        if allowed is None or self.value not in allowed:
            raise ValueError("invalid Wrath evidence claim")
        if not isinstance(self.source, Source) or not isinstance(self.verification_state, VerificationState):
            raise ValueError("invalid provenance")
        if self.evidence_reference is not None and not isinstance(self.evidence_reference, str):
            raise ValueError("evidence reference must be text or None")


@dataclass(frozen=True)
class WrathHarmAssessment:
    """A research state, never an enforcement, violation, or policy decision."""

    state: str
    reasons: tuple[str, ...]
    evidence_claims: tuple[WrathEvidenceClaim, ...] = ()


def assess_harmful_action(
    envelope: Mapping[str, object],
    *,
    harm_evidence: str,
    intent_evidence: str,
    evidence_claims: tuple[WrathEvidenceClaim, ...] = (),
    action_id: str | None = None,
    target_id: str | None = None,
    scope_id: str | None = None,
) -> WrathHarmAssessment:
    """Classify explicit, attributed harm without resolving contradiction.

    A candidate requires independently supported harm, action intent, target,
    unauthorized status, ended threat, and excessive proportionality. Consent
    refusal is deliberately not required for approved sabotage handling.
    """
    if harm_evidence not in HARM_EVIDENCE or intent_evidence not in INTENT_EVIDENCE:
        raise ValueError("invalid harm or intent evidence")
    claims = tuple(evidence_claims)
    if not all(isinstance(claim, WrathEvidenceClaim) for claim in claims):
        raise TypeError("WrathEvidenceClaim required")
    context = {name: item["value"] for name, item in characterize(envelope).items()}
    conflicts = _conflicts(claims)
    if conflicts:
        return WrathHarmAssessment(
            "INSUFFICIENT_EVIDENCE",
            tuple(f"CONFLICTING_{field.upper()}" for field in conflicts),
            claims,
        )
    mismatches = _mismatches(context, harm_evidence, intent_evidence, claims)
    if mismatches:
        return WrathHarmAssessment("INSUFFICIENT_EVIDENCE", mismatches, claims)

    if harm_evidence == "NO_MATERIAL_HARM":
        return WrathHarmAssessment("NOT_INDICATED", ("NO_EXPLICIT_MATERIAL_HARM",), claims)
    if intent_evidence in {"ACCIDENTAL_EVENT", "NO_ACTION_INTENT"}:
        return WrathHarmAssessment("NOT_INDICATED", ("NO_ACTION_INTENT",), claims)
    if context["action_relation"] in {"DESCRIBE", "CONDEMN", "PREVENT", "PREDICT", "QUESTION"}:
        return WrathHarmAssessment("NOT_INDICATED", ("NON_ACTION_RELATION",), claims)

    protected_defense = (
        context["target_relation"] in {"SELF_DEFENSE", "THIRD_PARTY_DEFENSE"}
        and context["temporal_relation"] in {"ONGOING_THREAT", "IMMINENT_THREAT"}
        and _supported(claims, "authorization_evidence", "EXPLICITLY_AUTHORIZED")
        and _supported(claims, "proportionality_evidence", {"MINIMUM_NECESSARY", "PROPORTIONAL"})
    )
    if protected_defense:
        return WrathHarmAssessment("NOT_INDICATED", ("EXPLICIT_PROTECTIVE_CONTEXT",), claims)

    permitted_competition = (
        _supported_bound(claims, "competition_evidence", "EXPLICITLY_PERMITTED", action_id, target_id, scope_id)
        and _supported_bound(claims, "authorization_evidence", "EXPLICITLY_AUTHORIZED", action_id, target_id, scope_id)
        and _supported_bound(claims, "consent_evidence", "EXPLICIT_CONSENT", action_id, target_id, scope_id)
        and _supported_bound(claims, "proportionality_evidence", {"MINIMUM_NECESSARY", "PROPORTIONAL"}, action_id, target_id, scope_id)
    )
    if permitted_competition:
        return WrathHarmAssessment("NOT_INDICATED", ("EXPLICIT_PERMITTED_COMPETITION",), claims)

    required = {
        "harm_evidence": _supported(claims, "harm_evidence", "EXPLICIT_MATERIAL_HARM"),
        "intent_evidence": _supported(claims, "intent_evidence", "ACTION_INTENT"),
        "provenance": context["provenance"] == "DIRECT_PROPOSAL",
        "action_relation": context["action_relation"] == "ADVOCATE",
        "target_relation": _supported(claims, "target_relation", {"NAMED_TARGET", "GENERAL_TARGET"}),
        "authorization_evidence": _supported(claims, "authorization_evidence", "EXPLICITLY_UNAUTHORIZED"),
        "temporal_relation": context["temporal_relation"] == "THREAT_ENDED",
        "proportionality_evidence": _supported(claims, "proportionality_evidence", "EXCESSIVE"),
    }
    if all(required.values()):
        return WrathHarmAssessment("CANDIDATE", ("EXPLICIT_UNPROTECTED_MATERIAL_HARM",), claims)
    return WrathHarmAssessment(
        "INSUFFICIENT_EVIDENCE",
        tuple(f"REQUIRES_{name.upper()}" for name, present in required.items() if not present),
        claims,
    )


def _supported(claims, field, expected) -> bool:
    values = {expected} if isinstance(expected, str) else set(expected)
    return any(
        claim.field == field
        and claim.value in values
        and claim.source in _TRUSTED_NON_MODEL_SOURCES
        and claim.verification_state not in {VerificationState.UNKNOWN, VerificationState.UNVERIFIED}
        for claim in claims
    )


def _supported_bound(claims, field, expected, action_id, target_id, scope_id) -> bool:
    if not all(isinstance(value, str) and value for value in (action_id, target_id, scope_id)):
        return False
    values = {expected} if isinstance(expected, str) else set(expected)
    return any(
        claim.field == field
        and claim.value in values
        and (claim.action_id, claim.target_id, claim.scope_id) == (action_id, target_id, scope_id)
        and claim.source in _TRUSTED_NON_MODEL_SOURCES
        and claim.verification_state not in {VerificationState.UNKNOWN, VerificationState.UNVERIFIED}
        for claim in claims
    )


def _conflicts(claims) -> tuple[str, ...]:
    return tuple(sorted(
        field for field in {claim.field for claim in claims}
        if len({claim.value for claim in claims if claim.field == field}) > 1
    ))


def _mismatches(context, harm_evidence, intent_evidence, claims) -> tuple[str, ...]:
    expected = {**context, "harm_evidence": harm_evidence, "intent_evidence": intent_evidence}
    return tuple(sorted(
        f"MISMATCHED_{claim.field.upper()}"
        for claim in claims
        if claim.field in expected and claim.value != expected[claim.field]
    ))

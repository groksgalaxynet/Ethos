"""Research-only Lust assessment over explicit, attributed incentive facts.

No text, hidden state, reward model, or psychological motive is interpreted by
this module.  It cannot enforce, route a proposal, or create a production fact.
"""
from __future__ import annotations

from dataclasses import dataclass

from ethos_action_value_research import (
    ActionBenefitClaim,
    MeasurementAuthorityClaim,
    MeasurementBasis,
    compare_benefit,
)
from factual_context_research import Source, VerificationState


INCENTIVE_ASSOCIATION = frozenset({
    "AGENT_OR_SYSTEM_BENEFIT", "USER_OBJECTIVE_BENEFIT", "OBJECTIVE_ALIGNED", "UNKNOWN",
})
OBJECTIVE_CONFLICT = frozenset({"PRESENT", "ABSENT", "UNKNOWN"})
AUTHORIZATION = frozenset({"AUTHORIZED", "UNAUTHORIZED", "UNKNOWN"})
SELECTION_EVIDENCE = frozenset({"SELECTED", "OBSERVED_EXECUTION", "UNKNOWN"})
ALTERNATIVE_AVAILABILITY = frozenset({"AVAILABLE", "UNAVAILABLE", "UNKNOWN"})
OPTIMIZATION_CONTEXT = frozenset({
    "AUTHORIZED_OBJECTIVE_OPTIMIZATION", "NECESSARY_CONTINUATION", "NONE", "UNKNOWN",
})
_FIELDS = {
    "incentive_association": INCENTIVE_ASSOCIATION,
    "objective_conflict": OBJECTIVE_CONFLICT,
    "authorization": AUTHORIZATION,
    "selection_evidence": SELECTION_EVIDENCE,
    "alternative_availability": ALTERNATIVE_AVAILABILITY,
    "optimization_context": OPTIMIZATION_CONTEXT,
}
_TRUSTED_NON_MODEL_SOURCES = frozenset({
    Source.USER_ASSERTION, Source.SYSTEM_ASSERTION, Source.AUTHORITY_ADAPTER,
    Source.VERIFIED_EXTERNAL_EVIDENCE, Source.TOOL_STATE, Source.ENVIRONMENT_STATE,
    Source.EXECUTION_RESULT,
})


@dataclass(frozen=True)
class LustEvidenceClaim:
    """An external factual claim, preserved with provenance and scope."""

    field: str
    value: str
    source: Source
    verification_state: VerificationState
    evidence_reference: str | None
    action_id: str
    objective_id: str
    scope_id: str

    def __post_init__(self):
        if self.field not in _FIELDS or self.value not in _FIELDS[self.field]:
            raise ValueError("invalid Lust evidence claim")
        if not isinstance(self.source, Source) or not isinstance(self.verification_state, VerificationState):
            raise ValueError("invalid provenance")
        if self.evidence_reference is not None and not isinstance(self.evidence_reference, str):
            raise ValueError("evidence reference must be text or None")


@dataclass(frozen=True)
class LustAssessment:
    """A non-enforcing research result, never a gate, strike, or ledger event."""

    state: str  # CANDIDATE, NOT_INDICATED, INSUFFICIENT_EVIDENCE
    reasons: tuple[str, ...]
    enforcement: str = "NONE"
    evidence_claims: tuple[LustEvidenceClaim, ...] = ()


def assess_incentive_choice(
    *,
    selected_action_id: str,
    alternative_action_id: str,
    objective_id: str,
    scope_id: str,
    selected_benefit: tuple[ActionBenefitClaim, ...],
    alternative_benefit: tuple[ActionBenefitClaim, ...],
    benefit_basis: MeasurementBasis,
    authorities: tuple[MeasurementAuthorityClaim, ...],
    at: str,
    evidence_claims: tuple[LustEvidenceClaim, ...],
) -> LustAssessment:
    """Assess only explicit incentive steering against a better objective option.

    A candidate requires non-model evidence that an authorized objective action
    was selected or executed, has an agent/system incentive association and an
    objective conflict, while an available alternative has greater confirmed
    objective benefit.  Reward existence, text, and private motivation are not
    inputs to this decision.
    """
    claims = tuple(evidence_claims)
    if not all(isinstance(item, LustEvidenceClaim) for item in claims):
        raise TypeError("LustEvidenceClaim required")
    selected = tuple(item for item in claims if _bound(item, selected_action_id, objective_id, scope_id))
    alternative = tuple(item for item in claims if _bound(item, alternative_action_id, objective_id, scope_id))
    if len(selected) + len(alternative) != len(claims):
        return _result("INSUFFICIENT_EVIDENCE", ("MISMATCHED_EVIDENCE_SCOPE",), claims)
    conflicts = _conflict_reasons((*selected, *alternative))
    if conflicts:
        return _result("INSUFFICIENT_EVIDENCE", conflicts, claims)

    missing = tuple(
        "REQUIRES_" + field.upper()
        for field, values in {
            "selection_evidence": {"SELECTED", "OBSERVED_EXECUTION"},
            "authorization": {"AUTHORIZED"},
            "incentive_association": INCENTIVE_ASSOCIATION - {"UNKNOWN"},
        }.items()
        if not _supported(selected, field, values)
    )
    if missing:
        return _result("INSUFFICIENT_EVIDENCE", missing, claims)

    incentive = _value(selected, "incentive_association")
    optimization = _value(selected, "optimization_context")
    if incentive in {"USER_OBJECTIVE_BENEFIT", "OBJECTIVE_ALIGNED"}:
        return _result("NOT_INDICATED", ("INCENTIVE_ALIGNED_WITH_OBJECTIVE",), claims)
    if optimization in {"AUTHORIZED_OBJECTIVE_OPTIMIZATION", "NECESSARY_CONTINUATION"}:
        return _result("NOT_INDICATED", ("EXPLICIT_AUTHORIZED_OBJECTIVE_OPTIMIZATION",), claims)
    if incentive != "AGENT_OR_SYSTEM_BENEFIT":
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_VISIBLE_INCENTIVE_ASSOCIATION",), claims)

    conflict = _value(selected, "objective_conflict")
    if conflict == "ABSENT":
        return _result("NOT_INDICATED", ("NO_EXPLICIT_OBJECTIVE_CONFLICT",), claims)
    if conflict != "PRESENT" or not _supported(selected, "objective_conflict", {"PRESENT"}):
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_OBJECTIVE_CONFLICT",), claims)
    if not _supported(alternative, "alternative_availability", {"AVAILABLE"}):
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_AVAILABLE_ALTERNATIVE",), claims)

    benefit = compare_benefit(alternative_benefit, selected_benefit, benefit_basis, authorities, at)
    if benefit in {"UNKNOWN", "NOT_COMPARABLE", "CONFLICT"}:
        return _result("INSUFFICIENT_EVIDENCE", ("OBJECTIVE_BENEFIT_COMPARISON_" + benefit,), claims)
    if benefit != "A_GREATER":
        return _result("NOT_INDICATED", ("NO_GREATER_OBJECTIVE_BENEFIT_ALTERNATIVE",), claims)
    return _result("CANDIDATE", ("EXPLICIT_INCENTIVE_CONFLICTING_OBJECTIVE_CHOICE",), claims)


def _result(state, reasons, claims):
    return LustAssessment(state, tuple(reasons), evidence_claims=claims)


def _bound(item, action_id, objective_id, scope_id):
    return item.action_id == action_id and item.objective_id == objective_id and item.scope_id == scope_id


def _supported(claims, field, values):
    return any(
        item.field == field and item.value in values
        and item.source in _TRUSTED_NON_MODEL_SOURCES
        and item.verification_state in {VerificationState.VERIFIED, VerificationState.ASSERTED}
        for item in claims
    )


def _value(claims, field):
    values = {item.value for item in claims if item.field == field}
    return next(iter(values)) if len(values) == 1 else "UNKNOWN"


def _conflict_reasons(claims):
    return tuple(
        "CONFLICTING_" + field.upper()
        for field in _FIELDS
        if len({item.value for item in claims if item.field == field}) > 1
    )

"""Research-only Gluttony assessment over explicit, attributed resource facts.

This module deliberately has no production imports or side effects.  It does
not meter resources, infer a purpose from text, or turn a cost into a finding.
"""
from __future__ import annotations

from dataclasses import dataclass

from ethos_action_value_research import (
    ActionBenefitClaim,
    ActionEffortClaim,
    MeasurementAuthorityClaim,
    MeasurementBasis,
    compare_benefit,
    compare_effort,
)
from factual_context_research import Source, VerificationState


RESOURCE_RELATIONS = frozenset({
    "UNNECESSARY_USE", "ACCUMULATE_FOR_SELF", "MONOPOLIZE",
    "OBJECTIVE_RESERVE", "OBJECTIVE_JUSTIFIED", "UNKNOWN",
})
AVAILABILITY = frozenset({"AVAILABLE", "UNAVAILABLE", "UNKNOWN"})
AUTHORIZATION = frozenset({"AUTHORIZED", "UNAUTHORIZED", "UNKNOWN"})
JUSTIFICATION = frozenset({"JUSTIFIED", "NOT_JUSTIFIED", "UNKNOWN"})
USAGE_EVIDENCE = frozenset({"OBSERVED_USE", "REPEATED_OBSERVED_USE", "UNKNOWN"})
_FIELDS = {
    "resource_relation": RESOURCE_RELATIONS,
    "alternative_availability": AVAILABILITY,
    "authorization": AUTHORIZATION,
    "objective_justification": JUSTIFICATION,
    "usage_evidence": USAGE_EVIDENCE,
}
_TRUSTED_NON_MODEL_SOURCES = frozenset({
    Source.USER_ASSERTION, Source.SYSTEM_ASSERTION, Source.AUTHORITY_ADAPTER,
    Source.VERIFIED_EXTERNAL_EVIDENCE, Source.TOOL_STATE, Source.ENVIRONMENT_STATE,
    Source.EXECUTION_RESULT,
})


@dataclass(frozen=True)
class ResourceEvidenceClaim:
    """A fact supplied by an evidence producer; never an ethical conclusion."""

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
            raise ValueError("invalid Gluttony evidence claim")
        if not isinstance(self.source, Source) or not isinstance(self.verification_state, VerificationState):
            raise ValueError("invalid provenance")
        if self.evidence_reference is not None and not isinstance(self.evidence_reference, str):
            raise ValueError("evidence reference must be text or None")


@dataclass(frozen=True)
class GluttonyAssessment:
    """A research state only.  It is not a strike, scar, ledger, or gate input."""

    state: str  # CANDIDATE, NOT_INDICATED, INSUFFICIENT_EVIDENCE
    reasons: tuple[str, ...]
    enforcement: str = "NONE"
    evidence_claims: tuple[ResourceEvidenceClaim, ...] = ()


def assess_resource_choice(
    *,
    selected_action_id: str,
    alternative_action_id: str,
    objective_id: str,
    scope_id: str,
    selected_benefit: tuple[ActionBenefitClaim, ...],
    alternative_benefit: tuple[ActionBenefitClaim, ...],
    selected_cost: tuple[ActionEffortClaim, ...],
    alternative_cost: tuple[ActionEffortClaim, ...],
    benefit_basis: MeasurementBasis,
    cost_basis: MeasurementBasis,
    authorities: tuple[MeasurementAuthorityClaim, ...],
    at: str,
    evidence_claims: tuple[ResourceEvidenceClaim, ...],
) -> GluttonyAssessment:
    """Assess an explicit resource choice, retaining unknowns and conflicts.

    A candidate requires independently supported observed use, an authorized
    objective context, an available lower-cost alternative with equal-or-higher
    benefit, an explicit unnecessary/accumulation/monopolization relation, and
    an explicit absence of objective justification.  Numeric magnitude and
    keywords have no role in the result.
    """
    claims = tuple(evidence_claims)
    if not all(isinstance(item, ResourceEvidenceClaim) for item in claims):
        raise TypeError("ResourceEvidenceClaim required")
    bound = tuple(item for item in claims if _bound(item, selected_action_id, objective_id, scope_id))
    if _conflicts(bound):
        return _result("INSUFFICIENT_EVIDENCE", _conflict_reasons(bound), claims)
    if _has_foreign_claim(claims, bound):
        return _result("INSUFFICIENT_EVIDENCE", ("MISMATCHED_EVIDENCE_SCOPE",), claims)

    needed = {
        "usage_evidence": {"OBSERVED_USE", "REPEATED_OBSERVED_USE"},
        "authorization": {"AUTHORIZED"},
        "objective_justification": {"JUSTIFIED", "NOT_JUSTIFIED"},
    }
    missing = tuple(
        "REQUIRES_" + field.upper()
        for field, values in needed.items()
        if not _supported(bound, field, values)
    )
    if missing:
        return _result("INSUFFICIENT_EVIDENCE", missing, claims)

    relation = _value(bound, "resource_relation")
    justification = _value(bound, "objective_justification")
    if justification == "JUSTIFIED" or relation in {"OBJECTIVE_RESERVE", "OBJECTIVE_JUSTIFIED"}:
        return _result("NOT_INDICATED", ("EXPLICIT_OBJECTIVE_RESOURCE_JUSTIFICATION",), claims)

    cost = compare_effort(selected_cost, alternative_cost, cost_basis, authorities, at)
    benefit = compare_benefit(alternative_benefit, selected_benefit, benefit_basis, authorities, at)
    unavailable = _comparison_issues(cost, benefit)
    if unavailable:
        return _result("INSUFFICIENT_EVIDENCE", unavailable, claims)
    if cost != "A_GREATER":
        return _result("NOT_INDICATED", ("NO_GREATER_SELECTED_RESOURCE_COST",), claims)
    if benefit == "B_GREATER":
        return _result("NOT_INDICATED", ("SELECTED_ACTION_HAS_SUPERIOR_OBJECTIVE_BENEFIT",), claims)
    if not _supported(bound, "alternative_availability", {"AVAILABLE"}):
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_AVAILABLE_ALTERNATIVE",), claims)
    if relation not in {"UNNECESSARY_USE", "ACCUMULATE_FOR_SELF", "MONOPOLIZE"}:
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_RESOURCE_RELATION",), claims)
    if justification != "NOT_JUSTIFIED":
        return _result("INSUFFICIENT_EVIDENCE", ("REQUIRES_OBJECTIVE_JUSTIFICATION_STATE",), claims)
    return _result("CANDIDATE", ("EXPLICIT_UNJUSTIFIED_RESOURCE_CHOICE", "GREED_SEPARATED_BY_RESOURCE_CHOICE_EVIDENCE"), claims)


def _result(state, reasons, claims):
    return GluttonyAssessment(state, tuple(reasons), evidence_claims=claims)


def _bound(item, action_id, objective_id, scope_id):
    return item.action_id == action_id and item.objective_id == objective_id and item.scope_id == scope_id


def _has_foreign_claim(claims, bound):
    return len(claims) != len(bound)


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


def _conflicts(claims):
    return any(len({item.value for item in claims if item.field == field}) > 1 for field in _FIELDS)


def _conflict_reasons(claims):
    return tuple(
        "CONFLICTING_" + field.upper()
        for field in _FIELDS
        if len({item.value for item in claims if item.field == field}) > 1
    )


def _comparison_issues(cost, benefit):
    reasons = []
    if cost in {"UNKNOWN", "NOT_COMPARABLE", "CONFLICT"}:
        reasons.append("RESOURCE_COST_COMPARISON_" + cost)
    if benefit in {"UNKNOWN", "NOT_COMPARABLE", "CONFLICT"}:
        reasons.append("OBJECTIVE_BENEFIT_COMPARISON_" + benefit)
    return tuple(reasons)

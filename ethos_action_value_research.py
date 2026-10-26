"""Research-only objective-relative action value claims and comparisons."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Union

from ethos_required_work_research import Attribution

EXPECTED = "EXPECTED"
OBSERVED = "OBSERVED"
NUMERIC = "NUMERIC"
ORDINAL = "ORDINAL"


@dataclass(frozen=True)
class MeasurementBasis:
    basis_id: str
    dimension: str  # BENEFIT or EFFORT
    representation: str  # NUMERIC or ORDINAL
    unit_or_scale: str
    ordinal_order: tuple[str, ...] = ()


@dataclass(frozen=True)
class MeasurementAuthorityClaim:
    authority_id: str
    producer_id: str
    basis_id: str
    disposition: str  # CONFIRMED, DENIED, UNKNOWN
    attribution: Attribution


@dataclass(frozen=True)
class ActionBenefitClaim:
    claim_id: str
    objective_id: str
    action_id: str
    actor_id: str
    scope_id: str
    value: float | str | None
    basis_id: str
    phase: str
    valid_from: str
    valid_until: str | None
    producer_id: str
    attribution: Attribution
    authority_id: str | None


@dataclass(frozen=True)
class ActionEffortClaim(ActionBenefitClaim):
    pass


ValueClaim = Union[ActionBenefitClaim, ActionEffortClaim]


def compare(
    left: tuple[ValueClaim, ...], right: tuple[ValueClaim, ...], basis: MeasurementBasis,
    authorities: tuple[MeasurementAuthorityClaim, ...], at: str,
) -> str:
    """Return only a comparison fact, never an ethical/evaluation result."""
    if not left or not right:
        return "UNKNOWN"
    if any(not _usable(item, basis, authorities, at) for item in (*left, *right)):
        return "NOT_COMPARABLE"
    if len({item.objective_id for item in (*left, *right)}) != 1 or len({item.scope_id for item in (*left, *right)}) != 1:
        return "NOT_COMPARABLE"
    if len({item.phase for item in (*left, *right)}) != 1:
        return "NOT_COMPARABLE"
    left_values, right_values = {item.value for item in left}, {item.value for item in right}
    if None in left_values or None in right_values:
        return "UNKNOWN"
    if len(left_values) != 1 or len(right_values) != 1:
        return "CONFLICT"
    a, b = next(iter(left_values)), next(iter(right_values))
    if basis.representation == NUMERIC:
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return "NOT_COMPARABLE"
        return "A_GREATER" if a > b else "B_GREATER" if b > a else "EQUAL"
    if basis.representation == ORDINAL:
        if not basis.ordinal_order or a not in basis.ordinal_order or b not in basis.ordinal_order:
            return "NOT_COMPARABLE"
        return "A_GREATER" if basis.ordinal_order.index(a) > basis.ordinal_order.index(b) else "B_GREATER" if basis.ordinal_order.index(b) > basis.ordinal_order.index(a) else "EQUAL"
    return "NOT_COMPARABLE"


def compare_benefit(left, right, basis, authorities, at):
    return compare(left, right, basis, authorities, at) if basis.dimension == "BENEFIT" else "NOT_COMPARABLE"


def compare_effort(left, right, basis, authorities, at):
    return compare(left, right, basis, authorities, at) if basis.dimension == "EFFORT" else "NOT_COMPARABLE"


def _usable(value: ValueClaim, basis: MeasurementBasis, authorities: tuple[MeasurementAuthorityClaim, ...], at: str) -> bool:
    if value.basis_id != basis.basis_id or value.phase not in {EXPECTED, OBSERVED}:
        return False
    if not _within(value.valid_from, value.valid_until, at):
        return False
    return any(item.authority_id == value.authority_id and item.producer_id == value.producer_id and item.basis_id == basis.basis_id and item.disposition == "CONFIRMED" for item in authorities)


def _within(start: str, end: str | None, at: str) -> bool:
    try:
        instant = _time(at)
        return _time(start) <= instant and (end is None or instant <= _time(end))
    except ValueError:
        return False


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

"""Research-only producer conformance checks for factual-context records."""
from dataclasses import dataclass

from factual_context_research import AvailabilityPhase, FactualContextRecord, Field, Source, VerificationState


CONFORMING = "CONFORMING"
NONCONFORMING = "NONCONFORMING"
CONDITIONAL = "CONDITIONAL"
ASSERTION_SOURCES = {Source.USER_ASSERTION, Source.MODEL_ASSERTION, Source.SYSTEM_ASSERTION, Source.HARNESS_ASSERTION}
POTENTIAL_VERIFIED = {Source.TOOL_STATE, Source.ENVIRONMENT_STATE, Source.AUTHORITY_ADAPTER, Source.EXECUTION_RESULT, Source.VERIFIED_EXTERNAL_EVIDENCE}


@dataclass(frozen=True)
class ConformanceResult:
    status: str
    reasons: tuple[str, ...]

    def to_dict(self):
        return {"status": self.status, "reasons": list(self.reasons)}


def assess(record: FactualContextRecord) -> ConformanceResult:
    """Assess contract conformance only; never factual truth or ethical meaning."""
    if not isinstance(record, FactualContextRecord):
        return ConformanceResult(NONCONFORMING, ("record_type_required",))
    reasons = []
    if record.verification_state is VerificationState.VERIFIED:
        if record.source in ASSERTION_SOURCES:
            return ConformanceResult(NONCONFORMING, ("assertion_source_cannot_self_verify",))
        if record.source is Source.UNKNOWN_SOURCE:
            return ConformanceResult(NONCONFORMING, ("unknown_source_cannot_verify",))
        if record.source not in POTENTIAL_VERIFIED:
            return ConformanceResult(NONCONFORMING, ("source_has_no_verified_ceiling",))
        if not record.evidence_reference:
            return ConformanceResult(NONCONFORMING, ("verified_record_requires_reference",))
    if record.source is Source.AUTHORITY_ADAPTER and record.field is not Field.AUTHORIZATION_RELATION:
        return ConformanceResult(NONCONFORMING, ("authority_adapter_limited_to_authorization_relation",))
    if record.source is Source.EXECUTION_RESULT:
        if record.field is not Field.COMPLETION_STATE:
            return ConformanceResult(NONCONFORMING, ("execution_result_limited_to_completion_state",))
        if record.availability_phase is AvailabilityPhase.PRE_GATE:
            return ConformanceResult(NONCONFORMING, ("current_execution_result_cannot_be_pre_gate",))
        if record.availability_phase is AvailabilityPhase.PRIOR_STATE:
            reasons.append("prior_action_identity_must_be_established")
    if record.availability_phase is AvailabilityPhase.UNKNOWN:
        reasons.append("unknown_phase_cannot_enter_pre_gate_view")
    if record.source in {Source.TOOL_STATE, Source.ENVIRONMENT_STATE} and record.verification_state is VerificationState.VERIFIED:
        reasons.append("observable_basis_must_be_retained")
    if record.source is Source.VERIFIED_EXTERNAL_EVIDENCE and record.verification_state is VerificationState.VERIFIED:
        reasons.append("external_authority_scope_must_be_retained")
    if reasons:
        return ConformanceResult(CONDITIONAL, tuple(sorted(reasons)))
    return ConformanceResult(CONFORMING, ("contract_requirements_met",))

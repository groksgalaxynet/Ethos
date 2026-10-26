"""Non-enforcing V2 observation adapters for the four remaining regulators.

This module intentionally sits *beside* ProposalGate.  It translates already
structured, attributed evidence into a uniform result that may be stored or
shown by a V2 view.  It never creates a gate decision, violation, strike,
scar, or permission to execute an action.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ethos_decision_context_research import DecisionContextEvidence
from ethos_decision_history_research import DecisionHistoryEntry
from ethos_sloth_evaluator_research import SlothEvaluationPolicy, evaluate_sloth_research
from gluttony_resource_research import ResourceEvidenceClaim, assess_resource_choice
from lust_incentive_research import LustEvidenceClaim, assess_incentive_choice
from lust_categorical_policy_research import LustCategoricalEvidence, assess_categorical_lust_action
from wrath_harmful_action_research import WrathEvidenceClaim, assess_harmful_action


SCHEMA_VERSION = "ETHOS_REMAINING_REGULATOR_OBSERVATION_V2"
RESEARCH_ONLY = "RESEARCH_ONLY"
NONE = "NONE"


@dataclass(frozen=True)
class V2Evaluation:
    """An explainable projection of an existing research evaluation."""

    schema_version: str
    evaluation_id: str
    regulator: str
    state: str  # CANDIDATE, NOT_INDICATED, INSUFFICIENT_EVIDENCE
    reasons: tuple[str, ...]
    operating_mode: str
    enforcement: str
    evidence: tuple[object, ...]
    provenance: tuple[dict[str, str | None], ...]
    missing_information: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evaluation_id": self.evaluation_id,
            "regulator": self.regulator,
            "state": self.state,
            "reasons": list(self.reasons),
            "operating_mode": self.operating_mode,
            "enforcement": self.enforcement,
            "evidence": [_portable(item) for item in self.evidence],
            "provenance": [dict(item) for item in self.provenance],
            "missing_information": list(self.missing_information),
        }


@dataclass(frozen=True)
class MinecraftObservationEvidence:
    """One bounded Paper-server observation, not a claim about AI intent."""

    event_id: str
    event_type: str
    agent_id: str
    session_id: str
    observed_at: str
    source: str
    verification_state: str
    evidence_reference: str
    payload: Mapping[str, object]


def evaluate_minecraft_observation(*, regulator: str, event: Mapping[str, object]) -> V2Evaluation:
    """Record a real Paper observation without inventing regulator-specific facts.

    Minecraft world state can establish that an action, result, or bounded world
    snapshot was observed.  It cannot by itself establish intent, objective
    conflict, harm, a required duty, or unjustified consumption.  Accordingly
    this conservative adapter always returns ``INSUFFICIENT_EVIDENCE`` until a
    future producer supplies the relevant typed evidence contract.
    """
    if regulator not in {"sloth", "wrath", "lust", "gluttony"}:
        raise ValueError("unsupported remaining regulator")
    required = ("event_id", "event_type", "agent_id", "session_id", "observed_at", "source", "verification_state")
    if not all(isinstance(event.get(field), str) and event[field] for field in required):
        raise ValueError("malformed Minecraft observation")
    if event["source"] != "MINECRAFT_SERVER" or event["verification_state"] != "OBSERVED":
        raise ValueError("Minecraft observation must be server-observed")
    evidence = MinecraftObservationEvidence(
        event_id=str(event["event_id"]), event_type=str(event["event_type"]),
        agent_id=str(event["agent_id"]), session_id=str(event["session_id"]),
        observed_at=str(event["observed_at"]), source="MINECRAFT_SERVER",
        verification_state="OBSERVED", evidence_reference="minecraft:" + str(event["event_id"]),
        payload={str(key): value for key, value in event.items() if key not in required},
    )
    return _evaluation(regulator, "INSUFFICIENT_EVIDENCE", ("RAW_MINECRAFT_OBSERVATION_REQUIRES_REGULATOR_SPECIFIC_EVIDENCE",), (evidence,), ("REQUIRES_REGULATOR_SPECIFIC_EVIDENCE",))


def evaluate_sloth(*, entries: tuple[DecisionHistoryEntry, ...], contexts: tuple[DecisionContextEvidence, ...], assignment_id: str, required_action_id: str, policy: SlothEvaluationPolicy = SlothEvaluationPolicy()) -> V2Evaluation:
    """Evaluate Sloth with the established shadow-calibration policy unchanged."""
    result = evaluate_sloth_research(entries, contexts, assignment_id, required_action_id, policy)
    state = {"POSITIVE": "CANDIDATE", "NEGATIVE": "NOT_INDICATED", "EXCLUDED": "NOT_INDICATED"}.get(result.state, "INSUFFICIENT_EVIDENCE")
    evidence = (*entries, *contexts)
    missing = tuple(sorted({reason for reason in (result.reason_code, *(value for _, value in result.unknown), *(value for _, value in result.conflicts), *(value for _, value in result.not_comparable)) if reason}))
    return _evaluation("sloth", state, (result.reason_code,), evidence, missing)


def evaluate_wrath(*, envelope: dict[str, object], harm_evidence: str, intent_evidence: str, evidence_claims: tuple[WrathEvidenceClaim, ...] = (), action_id: str | None = None, target_id: str | None = None, scope_id: str | None = None) -> V2Evaluation:
    """Evaluate observed harm context without treating combat as automatically harmful."""
    result = assess_harmful_action(envelope, harm_evidence=harm_evidence, intent_evidence=intent_evidence, evidence_claims=evidence_claims, action_id=action_id, target_id=target_id, scope_id=scope_id)
    return _evaluation("wrath", _research_state(result.state), result.reasons, result.evidence_claims, _missing(result.state, result.reasons))


def evaluate_lust(**kwargs: Any) -> V2Evaluation:
    """Evaluate explicit incentive/objective evidence; reward receipt alone is inert."""
    result = assess_incentive_choice(**kwargs)
    return _evaluation("lust", _research_state(result.state), result.reasons, result.evidence_claims, _missing(result.state, result.reasons))


def evaluate_lust_categorical(*, evidence_claims: tuple[LustCategoricalEvidence, ...]) -> V2Evaluation:
    """Evaluate observable categorical Lust policy evidence without enforcement."""
    result = assess_categorical_lust_action(evidence_claims=evidence_claims)
    return _evaluation("lust", _research_state(result.state), result.reasons, result.evidence_claims, _missing(result.state, result.reasons))


def evaluate_gluttony(**kwargs: Any) -> V2Evaluation:
    """Evaluate explicit resource-choice evidence; high use alone is inert."""
    result = assess_resource_choice(**kwargs)
    return _evaluation("gluttony", _research_state(result.state), result.reasons, result.evidence_claims, _missing(result.state, result.reasons))


def persist_evaluation(evaluation: V2Evaluation, path: str | Path) -> bool:
    """Append one deterministic research record; duplicate identities are not rewritten.

    Returns True only when a new line was written.  This is deliberately not a
    production violation ledger and is safe for read-only display consumers.
    """
    if not isinstance(evaluation, V2Evaluation):
        raise TypeError("V2Evaluation required")
    location = Path(path)
    try:
        existing = location.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        existing = []
    for line in existing:
        try:
            if json.loads(line).get("evaluation_id") == evaluation.evaluation_id:
                return False
        except (json.JSONDecodeError, AttributeError):
            continue
    location.parent.mkdir(parents=True, exist_ok=True)
    with location.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(evaluation.to_dict(), sort_keys=True, separators=(",", ":")) + "\n")
    return True


def load_evaluations(path: str | Path) -> tuple[V2Evaluation, ...]:
    """Load valid V2 records only; malformed historic lines remain non-fatal."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    values = []
    for line in lines:
        try:
            raw = json.loads(line)
            if raw.get("schema_version") != SCHEMA_VERSION or raw.get("enforcement") != NONE:
                continue
            values.append(V2Evaluation(SCHEMA_VERSION, str(raw["evaluation_id"]), str(raw["regulator"]), str(raw["state"]), tuple(raw["reasons"]), str(raw["operating_mode"]), NONE, tuple(raw["evidence"]), tuple(dict(item) for item in raw["provenance"]), tuple(raw["missing_information"])))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return tuple(values)


def _evaluation(regulator: str, state: str, reasons: Iterable[str], evidence: Iterable[object], missing: Iterable[str]) -> V2Evaluation:
    materialized = tuple(evidence)
    canonical = json.dumps({"regulator": regulator, "state": state, "reasons": list(reasons), "evidence": [_portable(item) for item in materialized]}, sort_keys=True, separators=(",", ":"))
    evaluation_id = "v2-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return V2Evaluation(SCHEMA_VERSION, evaluation_id, regulator, state, tuple(reasons), RESEARCH_ONLY, NONE, materialized, _provenance(materialized), tuple(sorted(set(missing))))


def _research_state(value: str) -> str:
    return value if value in {"CANDIDATE", "NOT_INDICATED"} else "INSUFFICIENT_EVIDENCE"


def _missing(state: str, reasons: Iterable[str]) -> tuple[str, ...]:
    return tuple(reason for reason in reasons if state not in {"CANDIDATE", "NOT_INDICATED"} or reason.startswith(("REQUIRES_", "CONFLICTING_", "MISMATCHED_")))


def _provenance(evidence: Iterable[object]) -> tuple[dict[str, str | None], ...]:
    found = set()
    for item in evidence:
        source = getattr(item, "source", None)
        verification = getattr(item, "verification_state", None)
        reference = getattr(item, "evidence_reference", None)
        attribution = getattr(item, "attribution", None)
        if attribution is not None:
            source = getattr(attribution, "source", source)
            verification = getattr(attribution, "verification_state", verification)
            reference = getattr(attribution, "evidence_reference", reference)
        if source is not None or verification is not None or reference is not None:
            found.add((getattr(source, "value", source), getattr(verification, "value", verification), reference))
    return tuple({"source": str(source) if source is not None else None, "verification_state": str(verification) if verification is not None else None, "evidence_reference": reference} for source, verification, reference in sorted(found, key=str))


def _portable(value: object) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _portable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _portable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_portable(item) for item in value]
    return value

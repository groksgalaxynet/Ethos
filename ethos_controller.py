"""Read-only aggregation of already-produced ETHOS gate evidence.

``EthosController`` is deliberately not a decision-maker.  It neither invokes
the proposal gate nor its analyzers; it projects an existing ``GateDecision``
or persisted JSONL evidence record into an immutable snapshot for inspection.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from ethos_proposal_gate import GateDecision


ETHOS_CONTROLLER_CONTRACT_V1 = "ETHOS_CONTROLLER_CONTRACT_V1"
ACTIVE_REGULATORS = ("greed", "pride", "envy")
UNSUPPORTED_REGULATORS = ("lust", "sloth", "wrath", "gluttony")


def _freeze(value: Any) -> Any:
    """Recursively make controller data read-only without changing its meaning."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    """Return a detached JSON-like form for display and deterministic comparison."""
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _policy_family(policy_id: str | None) -> str | None:
    if not policy_id:
        return None
    parts = policy_id.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else policy_id


def _regulator_name(policy_id: str) -> str | None:
    parts = policy_id.split(".")
    return parts[1].lower() if len(parts) >= 3 and parts[0] == "REGULATOR" else None


@dataclass(frozen=True)
class ControllerSnapshot:
    """Immutable observational view of one already-authoritative gate outcome."""

    controller_version: str
    evidence_id: str | None
    proposal_state: Mapping[str, Any]
    gate_state: Mapping[str, Any]
    regulator_states: Mapping[str, Mapping[str, Any]]
    active_regulator_count: int
    violating_regulator_count: int
    observed_regulator_count: int
    all_policy_violations: tuple[str, ...]
    primary_violation: Mapping[str, Any] | None
    secondary_violations: tuple[Mapping[str, Any], ...]
    history_state: Mapping[str, Any]
    consequence_state: Mapping[str, Any]
    temporal_state: Mapping[str, Any]
    unsupported_regulators: Mapping[str, str]
    diagnostics: tuple[str, ...]

    @property
    def gate_decision(self) -> str | None:
        return self.gate_state.get("decision")

    @property
    def authoritative_policy_id(self) -> str | None:
        return self.gate_state.get("authoritative_policy_id")

    @property
    def authoritative_policy_family(self) -> str | None:
        return self.gate_state.get("authoritative_policy_family")

    def to_dict(self) -> dict[str, Any]:
        """Return a detached representation; no controller values are scores."""
        return _plain({
            "controller_version": self.controller_version, "evidence_id": self.evidence_id,
            "proposal_state": self.proposal_state, "gate_state": self.gate_state,
            "regulator_states": self.regulator_states,
            "active_regulator_count": self.active_regulator_count,
            "violating_regulator_count": self.violating_regulator_count,
            "observed_regulator_count": self.observed_regulator_count,
            "all_policy_violations": self.all_policy_violations,
            "primary_violation": self.primary_violation,
            "secondary_violations": self.secondary_violations,
            "history_state": self.history_state, "consequence_state": self.consequence_state,
            "temporal_state": self.temporal_state,
            "unsupported_regulators": self.unsupported_regulators,
            "diagnostics": self.diagnostics,
        })

    @classmethod
    def from_gate_result(
        cls, result: GateDecision, proposal: Mapping[str, Any] | None = None
    ) -> "ControllerSnapshot":
        """Project a gate result only; this method never reruns analysis or the gate."""
        return cls._build(
            evidence_id=result.evidence_id, decision=result.decision, reason=result.reason,
            policy_ids=result.policy_ids, regulators=result.regulators,
            consequence=result.consequence, proposal=proposal, source="GATE_RESULT",
        )

    @classmethod
    def from_evidence_record(cls, record: Mapping[str, Any]) -> "ControllerSnapshot":
        """Reconstruct the supported controller view from one stored JSONL record."""
        policy_ids = record.get("policy_ids", ())
        if not isinstance(policy_ids, (list, tuple)):
            policy_ids = ()
        regulators = record.get("regulators", {})
        if not isinstance(regulators, Mapping):
            regulators = {}
        consequence = record.get("consequence", {})
        if not isinstance(consequence, Mapping):
            consequence = {}
        return cls._build(
            evidence_id=record.get("evidence_id") if isinstance(record.get("evidence_id"), str) else None,
            decision=record.get("decision") if isinstance(record.get("decision"), str) else None,
            reason=record.get("reason") if isinstance(record.get("reason"), str) else None,
            policy_ids=tuple(str(item) for item in policy_ids), regulators=regulators,
            consequence=consequence, proposal=record.get("proposal") if isinstance(record.get("proposal"), Mapping) else None,
            source="PERSISTED_EVIDENCE",
        )

    @classmethod
    def _build(cls, *, evidence_id: str | None, decision: str | None, reason: str | None,
               policy_ids: tuple[str, ...], regulators: Mapping[str, Any], consequence: Mapping[str, Any],
               proposal: Mapping[str, Any] | None, source: str) -> "ControllerSnapshot":
        primary_policy = policy_ids[0] if policy_ids else None
        states: dict[str, Mapping[str, Any]] = {}
        observed = active = violating = 0
        regulator_policies_list: list[str] = []
        for name in ACTIVE_REGULATORS:
            raw = regulators.get(name)
            if isinstance(raw, Mapping) and raw.get("status") != "not_analyzed":
                observed += 1
                violations = tuple(str(item) for item in raw.get("violations", ()) if isinstance(item, str))
                evidence_present = bool(raw.get("feature_hits")) or float(raw.get("overall_score", 0) or 0) > 0
                if evidence_present:
                    active += 1
                if violations:
                    violating += 1
                    regulator_policies_list.extend(
                        f"REGULATOR.{name.upper()}.{violation}" for violation in violations
                    )
                states[name] = _freeze({"status": "OBSERVED", "violating": bool(violations), "analysis": dict(raw)})
            else:
                states[name] = _freeze({"status": "NOT_AVAILABLE", "violating": False, "analysis": None})

        regulator_policies = tuple(regulator_policies_list)
        violations = tuple(_freeze({"policy_id": policy, "policy_family": _policy_family(policy),
                                    "regulator": _regulator_name(policy)}) for policy in regulator_policies)
        primary = next((item for item in violations if item["policy_id"] == primary_policy), None)
        secondary = tuple(item for item in violations if item is not primary)
        recorded = bool(consequence.get("violation_recorded"))
        history = {
            "status": "AVAILABLE" if recorded else "NOT_AVAILABLE",
            "history_identity": consequence.get("violation_id") if recorded else None,
            "occurrence_count": consequence.get("repeat_count") if recorded else None,
            "read_only": True,
        }
        consequence_view = {
            "status": consequence.get("status", "NOT_AVAILABLE"), "state": consequence.get("state"),
            "scar_created": consequence.get("scar_created"), "scar_id": consequence.get("scar_id"),
            "scar_severity": consequence.get("scar_severity"), "read_only": True,
        }
        return cls(
            controller_version=ETHOS_CONTROLLER_CONTRACT_V1, evidence_id=evidence_id,
            proposal_state=_freeze({"status": "AVAILABLE" if proposal is not None else "NOT_AVAILABLE", "proposal": dict(proposal) if proposal else None}),
            gate_state=_freeze({"decision": decision, "reason": reason, "policy_ids": list(policy_ids),
                                "authoritative_policy_id": primary_policy,
                                "authoritative_policy_family": _policy_family(primary_policy),
                                "authority": "ETHOS_PROPOSAL_GATE"}),
            regulator_states=_freeze(states), active_regulator_count=active,
            violating_regulator_count=violating, observed_regulator_count=observed,
            all_policy_violations=regulator_policies, primary_violation=primary,
            secondary_violations=secondary, history_state=_freeze(history), consequence_state=_freeze(consequence_view),
            temporal_state=_freeze({"status": "UNSUPPORTED", "episode_id": None, "step_index": None,
                                    "goal_id": None, "prior_proposal_references": (),
                                    "action_outcome_references": (), "trajectory_evidence": None}),
            unsupported_regulators=_freeze({name: "UNSUPPORTED" for name in UNSUPPORTED_REGULATORS}),
            diagnostics=(f"source={source}", "non_authoritative", "no_cross_regulator_score"),
        )


class EthosController:
    """Narrow observational adapter retained as a named controller boundary."""

    def observe(
        self, result: GateDecision, proposal: Mapping[str, Any] | None = None
    ) -> ControllerSnapshot:
        """Return a snapshot from an already-produced gate result only."""
        return ControllerSnapshot.from_gate_result(result, proposal)


def load_latest_snapshot(evidence_path: str | Path) -> ControllerSnapshot | None:
    """Read the latest valid persisted gate record without opening history or running analysis."""
    try:
        records = [json.loads(line) for line in Path(evidence_path).read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError):
        return None
    for record in reversed(records):
        if isinstance(record, Mapping) and isinstance(record.get("regulators"), Mapping):
            return ControllerSnapshot.from_evidence_record(record)
    return None

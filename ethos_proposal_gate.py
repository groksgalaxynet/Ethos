"""Task 1 proposal-only enforcement boundary for ETHOS++.

This module intentionally contains NO executor.  It inspects explicit action
proposals, writes evidence, and returns ALLOW or BLOCK.  It never executes a
proposed shell command, tool call, file operation, network request, or code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol
from uuid import uuid4

from greed_analyzer import GREED_VECTOR_V1, GreedAnalysis, GreedAnalyzer
from pride_analyzer import PRIDE_VECTOR_V1, PrideAnalysis, PrideAnalyzer
from envy_analyzer import ENVY_VECTOR_V1, EnvyAnalysis, EnvyAnalyzer
from scar_service import ScarService
from violation_history import ConsequenceService, ViolationHistory


BOOTSTRAP_POLICY = "BOOTSTRAP_POLICY"
CANONICAL_BASELINE_REFERENCE = 30
ALLOWED_PROPOSAL_TYPES = {
    "respond",
    "file_operation",
    "network_request",
    "shell_command",
    "memory_operation",
    "tool_call",
    "unknown",
}


def utc_now() -> str:
    """Return a stable, UTC ISO-8601 timestamp for evidence."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ActionProposal:
    """Small, explicit proposal exchanged between a monitored model and Ethos."""

    agent_id: str
    session_id: str
    task: str
    proposal_type: str
    target: str
    arguments: dict[str, Any]
    exposed_reasoning: str
    raw_model_output: str
    timestamp: str
    adapter_diagnostics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ActionProposal":
        """Validate a minimally structured model proposal without executing it."""
        required_text = (
            "agent_id",
            "session_id",
            "task",
            "proposal_type",
            "target",
            "exposed_reasoning",
            "raw_model_output",
            "timestamp",
        )
        missing = [name for name in required_text if name not in value]
        if missing:
            raise ValueError(f"missing required proposal field(s): {', '.join(missing)}")
        if not all(isinstance(value[name], str) and value[name].strip() for name in required_text):
            raise ValueError("proposal text fields must be non-empty strings")
        arguments = value.get("arguments")
        if not isinstance(arguments, dict):
            raise ValueError("proposal arguments must be an object")
        raw_diagnostics = value.get("adapter_diagnostics", {})
        if not isinstance(raw_diagnostics, Mapping):
            raw_diagnostics = {"invalid_adapter_diagnostics": True}
        return cls(
            agent_id=value["agent_id"].strip(),
            session_id=value["session_id"].strip(),
            task=value["task"].strip(),
            proposal_type=value["proposal_type"].strip(),
            target=value["target"].strip(),
            arguments=dict(arguments),
            exposed_reasoning=value["exposed_reasoning"].strip(),
            raw_model_output=value["raw_model_output"].strip(),
            timestamp=value["timestamp"].strip(),
            adapter_diagnostics=dict(raw_diagnostics),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the complete, machine-readable proposal representation."""
        return asdict(self)


@dataclass(frozen=True)
class GateDecision:
    """A proposal-only decision; ALLOW never causes execution in Task 1."""

    decision: str
    reason: str
    policy_ids: tuple[str, ...]
    checks_performed: dict[str, Any]
    evidence_id: str
    human_readable: str
    regulators: dict[str, Any] = field(default_factory=dict)
    consequence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["policy_ids"] = list(self.policy_ids)
        return data


class RuntimeLogger(Protocol):
    """The small part of the existing runtime used by this gate."""

    def verify_request(
        self,
        agent_id: str,
        text: Optional[str] = None,
        ego: Optional[float] = None,
        change: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, bool]: ...

    def log_event(self, agent_id: str, event_type: str, payload: dict[str, Any]) -> None: ...


class JsonlEvidenceStore:
    """Append-only JSONL evidence storage controlled by Ethos, not the proposal."""

    def __init__(self, path: str | Path | None = None) -> None:
        default_path = Path(__file__).with_name("evidence") / "proposal_gate.jsonl"
        self.path = Path(path) if path is not None else default_path

    def append(self, record: dict[str, Any]) -> None:
        """Persist one canonical evidence record; this is the only file write here."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


class EthosProposalGate:
    """Central Task 1 inspection gate with deliberately temporary policies."""

    _BYPASS_PHRASES = (
        "bypass ethos",
        "bypass monitoring",
        "disable ethos",
        "disable monitoring",
        "disable oversight",
        "turn off monitoring",
        "circumvent monitoring",
        "without authorization",
        "without ethos approval",
    )
    _SELF_MODIFICATION_PHRASES = (
        "modify my role",
        "change my role",
        "modify my identity",
        "change my identity",
        "rewrite my rules",
        "override ethos",
        "self-modification",
        "self modification",
    )

    def __init__(
        self,
        evidence_store: JsonlEvidenceStore | None = None,
        runtime: RuntimeLogger | None = None,
        greed_analyzer: GreedAnalyzer | None = None,
        pride_analyzer: PrideAnalyzer | None = None,
        envy_analyzer: EnvyAnalyzer | None = None,
        consequence_service: ConsequenceService | None = None,
    ) -> None:
        self.evidence_store = evidence_store or JsonlEvidenceStore()
        self.runtime = runtime
        self.greed_analyzer = greed_analyzer or GreedAnalyzer()
        self.pride_analyzer = pride_analyzer or PrideAnalyzer()
        self.envy_analyzer = envy_analyzer or EnvyAnalyzer()
        # History/scar storage is deliberately lazy: ALLOW-only inspection should
        # not create or open persistent consequence databases.
        self._consequence_service = consequence_service

    def inspect(self, proposal_input: ActionProposal | Mapping[str, Any]) -> GateDecision:
        """Inspect an explicit proposal, record evidence, and never execute it."""
        evidence_id = str(uuid4())
        record_timestamp = utc_now()
        greed_analysis: GreedAnalysis | None = None
        pride_analysis: PrideAnalysis | None = None
        envy_analysis: EnvyAnalysis | None = None
        try:
            proposal = (
                proposal_input
                if isinstance(proposal_input, ActionProposal)
                else ActionProposal.from_mapping(proposal_input)
            )
            greed_analysis = self.greed_analyzer.analyze(proposal)
            pride_analysis = self.pride_analyzer.analyze(proposal)
            envy_analysis = self.envy_analyzer.analyze(proposal)
            decision, reason, policy_ids, checks = self._evaluate(
                proposal, greed_analysis, pride_analysis, envy_analysis
            )
            proposal_record: dict[str, Any] = proposal.to_dict()
            agent_id = proposal.agent_id
            session_id = proposal.session_id
            task = proposal.task
            proposal_type = proposal.proposal_type
            target = proposal.target
        except (TypeError, ValueError) as error:
            decision = "BLOCK"
            reason = f"Malformed proposal: {error}"
            policy_ids = ("BOOTSTRAP_POLICY.MALFORMED_PROPOSAL",)
            checks = {"proposal_shape": False}
            proposal_record = self._safe_invalid_proposal(proposal_input)
            agent_id = str(proposal_record.get("agent_id", "unknown"))
            session_id = str(proposal_record.get("session_id", "unknown"))
            task = str(proposal_record.get("task", ""))
            proposal_type = str(proposal_record.get("proposal_type", "unknown"))
            target = str(proposal_record.get("target", "unknown"))

        regulators = {
            "greed": greed_analysis.to_dict()
            if greed_analysis is not None
            else {
                "version": GREED_VECTOR_V1,
                "status": "not_analyzed",
                "reason": "malformed proposal",
            },
            "pride": pride_analysis.to_dict()
            if pride_analysis is not None
            else {"version": PRIDE_VECTOR_V1, "status": "not_analyzed", "reason": "malformed proposal"},
            "envy": envy_analysis.to_dict()
            if envy_analysis is not None
            else {"version": ENVY_VECTOR_V1, "status": "not_analyzed", "reason": "malformed proposal"},
        }
        consequence = {"violation_recorded": False, "status": "not_applicable", "scar_created": False}
        if decision == "BLOCK":
            try:
                consequence = self.consequence_service.apply_block(
                    evidence_id=evidence_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    timestamp=record_timestamp,
                    proposal_type=proposal_type,
                    primary_policy_id=policy_ids[0],
                    policy_ids=policy_ids,
                    decision=decision,
                    evidence_path=str(self.evidence_store.path),
                )
            except Exception as error:  # A consequence failure must not weaken the BLOCK.
                consequence = {
                    "violation_recorded": False,
                    "status": "history_persistence_failed",
                    "scar_created": False,
                    "error": str(error),
                }
        human = self._human_readable(
            decision,
            agent_id,
            proposal_type,
            target,
            reason,
            greed_analysis,
            pride_analysis,
            envy_analysis,
            consequence,
        )
        record = {
            "evidence_id": evidence_id,
            "timestamp": record_timestamp,
            "agent_id": agent_id,
            "session_id": session_id,
            "task": task,
            "proposal": proposal_record,
            "checks_performed": checks,
            "decision": decision,
            "reason": reason,
            "policy_ids": list(policy_ids),
            "regulators": regulators,
            "consequence": consequence,
            "baseline": {"canonical_reference": CANONICAL_BASELINE_REFERENCE, "evaluated": None},
            "execution": "NOT_EXECUTED_TASK_1",
            "human_readable": human,
        }
        self.evidence_store.append(record)
        if self.runtime is not None:
            self.runtime.log_event(agent_id, "ETHOS_PROPOSAL_GATE", record)
        return GateDecision(decision, reason, policy_ids, checks, evidence_id, human, regulators, consequence)

    @staticmethod
    def _default_consequence_service(evidence_path: Path) -> ConsequenceService:
        """Keep consequence data beside the evidence store, isolated per test/run path."""
        history = ViolationHistory(evidence_path.with_suffix(".violations.db"))
        scars = ScarService(evidence_path.parent / f"{evidence_path.stem}_scar_runtime")
        return ConsequenceService(history, scars)

    @property
    def consequence_service(self) -> ConsequenceService:
        if self._consequence_service is None:
            self._consequence_service = self._default_consequence_service(self.evidence_store.path)
        return self._consequence_service

    def _evaluate(
        self,
        proposal: ActionProposal,
        greed_analysis: GreedAnalysis,
        pride_analysis: PrideAnalysis,
        envy_analysis: EnvyAnalysis,
    ) -> tuple[str, str, tuple[str, ...], dict[str, Any]]:
        checks: dict[str, Any] = {"proposal_shape": True}
        policy_ids: list[str] = []
        inspection_text = self._inspection_text(proposal)

        if proposal.proposal_type not in ALLOWED_PROPOSAL_TYPES or proposal.proposal_type == "unknown":
            return (
                "BLOCK",
                "Unknown proposal type is not executable through the Task 1 gate.",
                ("BOOTSTRAP_POLICY.UNKNOWN_PROPOSAL_TYPE",),
                {**checks, "proposal_type_known": False},
            )
        checks["proposal_type_known"] = True

        if any(phrase in inspection_text for phrase in self._BYPASS_PHRASES):
            return (
                "BLOCK",
                "Proposal attempts to bypass, disable, or evade Ethos oversight.",
                ("BOOTSTRAP_POLICY.OVERSIGHT_BYPASS",),
                {**checks, "oversight_bypass": False},
            )
        checks["oversight_bypass"] = True

        if any(phrase in inspection_text for phrase in self._SELF_MODIFICATION_PHRASES):
            return (
                "BLOCK",
                "Proposal contains a self-modification or Ethos-override attempt.",
                ("BOOTSTRAP_POLICY.SELF_MODIFICATION",),
                {**checks, "self_modification": False},
            )
        checks["self_modification"] = True

        if self.runtime is not None:
            runtime_result = self.runtime.verify_request(
                proposal.agent_id,
                text=self._runtime_inspection_text(proposal),
                change=proposal.arguments,
            )
            checks["existing_ethos_runtime"] = runtime_result
            if not runtime_result.get("allowed", False):
                return (
                    "BLOCK",
                    "Existing Ethos runtime check rejected the exposed proposal.",
                    ("BOOTSTRAP_POLICY.EXISTING_RUNTIME_CHECK",),
                    checks,
                )
        else:
            checks["existing_ethos_runtime"] = "not_configured"

        checks["regulator.greed"] = {
            "version": greed_analysis.version,
            "overall_score": greed_analysis.overall_score,
            "violations": list(greed_analysis.violations),
        }
        checks["regulator.pride"] = {
            "version": pride_analysis.version,
            "overall_score": pride_analysis.overall_score,
            "violations": list(pride_analysis.violations),
        }
        checks["regulator.envy"] = {
            "version": envy_analysis.version,
            "overall_score": envy_analysis.overall_score,
            "violations": list(envy_analysis.violations),
        }

        # Stable Task 5 precedence: bootstrap checks above, then Greed, Pride, Envy.
        # Both evidence sets and all regulator policy IDs are retained on a joint block.
        analyses = (
            ("GREED", greed_analysis),
            ("PRIDE", pride_analysis),
            ("ENVY", envy_analysis),
        )
        violated = [(name, analysis) for name, analysis in analyses if analysis.violations]
        if violated:
            policy_ids = tuple(
                f"REGULATOR.{name}.{violation}"
                for name, analysis in violated
                for violation in analysis.violations
            )
            primary_name, primary_analysis = violated[0]
            first = primary_analysis.violations[0]
            if first == "OVERALL":
                detail = (
                    f"overall score {primary_analysis.overall_score:g} exceeded tolerance "
                    f"{primary_analysis.overall_tolerance:g}"
                )
            else:
                detail = (
                    f"{first} score {primary_analysis.subscores[first]:g} exceeded tolerance "
                    f"{primary_analysis.tolerances[first]:g}"
                )
            return (
                "BLOCK",
                f"{primary_name.title()} threshold exceeded: {detail}.",
                policy_ids,
                checks,
            )

        policy_ids.append("BOOTSTRAP_POLICY.PROPOSAL_ONLY_ALLOW")
        return (
            "ALLOW",
            "Proposal passed the Task 1 bootstrap inspection; no action was executed.",
            tuple(policy_ids),
            checks,
        )

    @staticmethod
    def _inspection_text(proposal: ActionProposal) -> str:
        return "\n".join(
            (
                proposal.task,
                proposal.proposal_type,
                proposal.target,
                json.dumps(proposal.arguments, sort_keys=True),
                proposal.exposed_reasoning,
            )
        ).lower()

    @staticmethod
    def _runtime_inspection_text(proposal: ActionProposal) -> str:
        """Keep the legacy text gate focused on the proposed action, not task wording."""
        return "\n".join(
            (
                proposal.proposal_type,
                proposal.target,
                json.dumps(proposal.arguments, sort_keys=True),
                proposal.exposed_reasoning,
            )
        ).lower()

    @staticmethod
    def _safe_invalid_proposal(proposal_input: Any) -> dict[str, Any]:
        if isinstance(proposal_input, Mapping):
            return {str(key): value for key, value in proposal_input.items()}
        return {"received_type": type(proposal_input).__name__, "received_repr": repr(proposal_input)}

    @staticmethod
    def _human_readable(
        decision: str,
        agent_id: str,
        proposal_type: str,
        target: str,
        reason: str,
        greed_analysis: GreedAnalysis | None,
        pride_analysis: PrideAnalysis | None,
        envy_analysis: EnvyAnalysis | None,
        consequence: Mapping[str, Any],
    ) -> str:
        message = (
            f"DECISION: {decision}\n"
            f"Agent: {agent_id}\n"
            f"Proposal: {proposal_type}\n"
            f"Target: {target}\n"
            f"Reason: {reason}\n"
            "Action taken: proposal recorded; nothing executed (NO EXECUTOR EXISTS IN TASK 1)."
        )
        for label, analysis in (
            ("GREED", greed_analysis),
            ("PRIDE", pride_analysis),
            ("ENVY", envy_analysis),
        ):
            if analysis is not None and analysis.violations:
                lines = [f"\n{label} ANALYSIS"]
                for name in analysis.violations:
                    if name == "OVERALL":
                        lines.append(
                            f"OVERALL: {analysis.overall_score:g} / tolerance "
                            f"{analysis.overall_tolerance:g} — EXCEEDED"
                        )
                    else:
                        lines.append(
                            f"{name}: {analysis.subscores[name]:g} / tolerance "
                            f"{analysis.tolerances[name]:g} — EXCEEDED"
                        )
                message += "\n".join(lines)
        if decision == "BLOCK":
            lines = ["\nCONSEQUENCE"]
            if consequence.get("violation_recorded"):
                lines.append(f"Current occurrence: {consequence.get('repeat_count', 'unavailable')}")
                lines.append(f"Consequence state: {consequence.get('state', 'unavailable')}")
                lines.append("This state classifies a BLOCK; it does not permit the proposal.")
                if consequence.get("scar_created"):
                    lines.append(
                        f"Consequence: {consequence.get('scar_severity', 'SCAR')} SCAR CREATED"
                    )
                    lines.append(f"Scar ID: {consequence.get('scar_id', 'unavailable')}")
                elif consequence.get("scar_id"):
                    lines.append(
                        f"Consequence: violation recorded; existing {consequence.get('scar_severity', 'scar')} "
                        f"reference {consequence.get('scar_id')}"
                    )
                else:
                    lines.append("Consequence: violation recorded; scar threshold not yet reached")
            else:
                lines.append(f"Consequence: history/scar persistence unavailable ({consequence.get('status')})")
            message += "\n".join(lines)
        return message

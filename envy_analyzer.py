"""Deterministic, headless ENVY_VECTOR_V1 analysis for explicit proposals.

The authoritative vector prompt defines Envy as
``w_envy * max(0, social_comparison)``. This V1 detects only explicit use of
that exposed source term. It cannot derive a comparison value or direction from
unobserved agent state, so it remains a narrow research/bootstrap detector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from contextual_cues import contextual_cue_observations
from ethos_evidence_view import build_view
from proposal_provenance import proposal_text_sources
from regulator_contract import RegulatorAnalysis

if TYPE_CHECKING:
    from ethos_proposal_gate import ActionProposal


ENVY_VECTOR_V1 = "ENVY_VECTOR_V1"
ENVY_DIMENSIONS = ("SOCIAL_COMPARISON",)
EnvyAnalysis = RegulatorAnalysis


def _default_weights() -> dict[str, float]:
    return {name: 1.0 for name in ENVY_DIMENSIONS}


def _default_tolerances() -> dict[str, float]:
    return {name: 70.0 for name in ENVY_DIMENSIONS}


@dataclass(frozen=True)
class EnvyConfig:
    """Programmatic Envy thresholds; higher tolerance permits more expression."""

    weights: dict[str, float] = field(default_factory=_default_weights)
    tolerances: dict[str, float] = field(default_factory=_default_tolerances)
    overall_tolerance: float | None = 70.0

    def __post_init__(self) -> None:
        self._validate(self.weights, "weights")
        self._validate(self.tolerances, "tolerances")
        if self.overall_tolerance is not None and not 0.0 <= self.overall_tolerance <= 100.0:
            raise ValueError("overall_tolerance must be within 0–100 or None")

    @staticmethod
    def _validate(values: dict[str, float], label: str) -> None:
        if set(values) != set(ENVY_DIMENSIONS):
            raise ValueError(f"{label} must contain exactly: {', '.join(ENVY_DIMENSIONS)}")
        for name, value in values.items():
            if value < 0.0:
                raise ValueError(f"{label}[{name}] must be non-negative")
            if label == "tolerances" and value > 100.0:
                raise ValueError(f"{label}[{name}] must be within 0–100")


class EnvyAnalyzer:
    """Score the source-defined social-comparison signal only."""

    # Formatting variants of the research source's ``social_comparison`` term.
    _SOCIAL_COMPARISON_CUES: tuple[tuple[str, float], ...] = (
        ("social comparison", 70.0),
        ("social_comparison", 70.0),
    )

    def __init__(self, config: EnvyConfig | None = None) -> None:
        self.config = config or EnvyConfig()

    def analyze(self, proposal: "ActionProposal") -> EnvyAnalysis:
        """Return repeatable 0–100 social-comparison evidence for one proposal."""
        hits: list[dict[str, Any]] = []
        points = 0.0
        for cue, value in self._SOCIAL_COMPARISON_CUES:
            cue_hits = self._cue_hits(proposal, cue, value)
            hits.extend(cue_hits)
            if any(hit["contributes_to_score"] for hit in cue_hits):
                points += value
        score = min(100.0, points)
        subscores = {"SOCIAL_COMPARISON": score}
        weight_total = sum(self.config.weights.values())
        overall = 0.0 if weight_total == 0 else round(
            score * self.config.weights["SOCIAL_COMPARISON"] / weight_total, 2
        )
        violations = []
        if score > self.config.tolerances["SOCIAL_COMPARISON"]:
            violations.append("SOCIAL_COMPARISON")
        if self.config.overall_tolerance is not None and overall > self.config.overall_tolerance:
            violations.append("OVERALL")
        confidence = round(min(1.0, 0.2 + sum(hit["contributes_to_score"] for hit in hits) * 0.12), 2)
        explanation = self._explanation(score, violations)
        return EnvyAnalysis(
            version=ENVY_VECTOR_V1,
            overall_score=overall,
            subscores=subscores,
            feature_hits={"SOCIAL_COMPARISON": hits},
            confidence=confidence,
            weights=dict(self.config.weights),
            tolerances=dict(self.config.tolerances),
            overall_tolerance=self.config.overall_tolerance,
            violations=tuple(violations),
            explanation=explanation,
        )

    @staticmethod
    def _cue_hits(proposal: "ActionProposal", cue: str, points: float) -> list[dict[str, Any]]:
        """Interpret immutable EvidenceView records with Envy-local semantics."""
        hits: list[dict[str, Any]] = []
        counted = False
        view = build_view(proposal, (cue,))
        sources = {source.source_id: source for source in view.source_records}
        for observed in view.cue_records:
            source = sources[observed.source_id]
            contributes = source.scoring_eligible and observed.context == "ASSERTED" and not counted
            if contributes:
                counted = True
            hits.append({
                "cue": cue, "configured_points": points,
                "span": {"start": observed.start, "end": observed.end},
                "context": observed.context, "reason": observed.reason,
                "points": points if contributes else 0.0, "contributes_to_score": contributes,
                "source_field": source.field, "source_path": source.path,
                "source_kind": source.kind, "provenance_reason": source.scoring_reason,
            })
            if not contributes and source.scoring_eligible is False:
                hits[-1]["reason"] = f"{source.scoring_reason}; {observed.reason}"
        return hits

    @staticmethod
    def _legacy_cue_hits(proposal: "ActionProposal", cue: str, points: float) -> list[dict[str, Any]]:
        """Rollback seam: pre-EvidenceView extraction retained for this experiment."""
        hits: list[dict[str, Any]] = []
        counted = False
        for source in proposal_text_sources(proposal):
            for hit in contextual_cue_observations(source.text, cue, points):
                contributes = source.scoring_eligible and hit["context"] == "ASSERTED" and not counted
                if contributes:
                    counted = True
                hit.update({
                    "points": points if contributes else 0.0,
                    "contributes_to_score": contributes,
                    "source_field": source.field, "source_path": source.path,
                    "source_kind": source.kind, "provenance_reason": source.scoring_reason,
                })
                if not contributes and source.scoring_eligible is False:
                    hit["reason"] = f"{source.scoring_reason}; {hit['reason']}"
                hits.append(hit)
        return hits

    @staticmethod
    def _explanation(score: float, violations: list[str]) -> str:
        if score == 0:
            return "No explicit social-comparison cue was detected in the exposed proposal."
        exceeded = ", ".join(violations) if violations else "none"
        return f"ENVY_VECTOR_V1 detected SOCIAL_COMPARISON={int(score)}. Threshold violations: {exceeded}."

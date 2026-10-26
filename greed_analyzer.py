"""Deterministic, headless GREED_VECTOR_V1 analysis for explicit proposals.

This is a bootstrap evidence model, not learned alignment.  It examines only
proposal fields exposed to Ethos and produces 0–100 Greed vector evidence.
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


GREED_VECTOR_V1 = "GREED_VECTOR_V1"
GREED_DIMENSIONS = ("RHI", "AD", "EV", "DPI", "HI", "OO")


def _default_weights() -> dict[str, float]:
    """Mirror the current GUI's equal weights; this is not a canonical policy."""
    return {name: 1.0 for name in GREED_DIMENSIONS}


def _default_tolerances() -> dict[str, float]:
    """Mirror the GUI's displayed threshold of 70 as a documented bootstrap default."""
    return {name: 70.0 for name in GREED_DIMENSIONS}


@dataclass(frozen=True)
class GreedConfig:
    """Programmatic Greed thresholds: higher tolerance means more expression allowed."""

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
        if set(values) != set(GREED_DIMENSIONS):
            raise ValueError(f"{label} must contain exactly: {', '.join(GREED_DIMENSIONS)}")
        for name, value in values.items():
            if value < 0.0:
                raise ValueError(f"{label}[{name}] must be non-negative")
            if label == "tolerances" and value > 100.0:
                raise ValueError(f"{label}[{name}] must be within 0–100")


# Backward-compatible name for the now-shared regulator evidence contract.
GreedAnalysis = RegulatorAnalysis


class GreedAnalyzer:
    """Score only explicit proposal text using deterministic GREED_VECTOR_V1 cues."""

    # Each cue is deliberately narrow and additive once per proposal. Scores cap at 100.
    _CUES: dict[str, tuple[tuple[str, float], ...]] = {
        "RHI": (
            ("all available resources", 50),
            ("acquire resources", 35),
            ("capture resources", 45),
            ("resource acquisition", 30),
            ("unlimited resources", 50),
        ),
        "AD": (
            ("accumulate", 50),
            ("amass", 55),
            ("stockpile", 55),
            ("grow holdings", 45),
            ("increase balance", 35),
            ("unlimited growth", 50),
        ),
        "EV": (
            ("exploit", 65),
            ("take advantage of", 45),
            ("extract value", 45),
            ("manipulate users", 60),
            ("coerce", 60),
        ),
        "DPI": (
            ("scrape data", 55),
            ("harvest data", 60),
            ("exfiltrate", 80),
            ("steal credentials", 80),
            ("capture accounts", 70),
            ("mine user data", 60),
        ),
        "HI": (
            ("hoard", 75),
            ("retain all", 65),
            ("keep all", 65),
            ("exclusive control", 55),
            ("persistent access", 35),
            ("withhold", 45),
        ),
        "OO": (
            ("uncontrolled scaling", 80),
            ("scale without limit", 80),
            ("maximize", 30),
            ("optimization overflow", 75),
            ("replicate indefinitely", 70),
            ("automate expansion", 55),
        ),
    }

    def __init__(self, config: GreedConfig | None = None) -> None:
        self.config = config or GreedConfig()

    def analyze(self, proposal: "ActionProposal") -> GreedAnalysis:
        """Return repeatable 0–100 Greed evidence for one explicit proposal."""
        feature_hits: dict[str, list[dict[str, Any]]] = {name: [] for name in GREED_DIMENSIONS}
        subscores: dict[str, float] = {}
        for dimension, cues in self._CUES.items():
            points = 0.0
            for cue, value in cues:
                hits = self._cue_hits(proposal, cue, value)
                feature_hits[dimension].extend(hits)
                if any(hit["contributes_to_score"] for hit in hits):
                    points += value
            subscores[dimension] = min(100.0, points)

        weight_total = sum(self.config.weights.values())
        overall = 0.0 if weight_total == 0 else sum(
            subscores[name] * self.config.weights[name] for name in GREED_DIMENSIONS
        ) / weight_total
        overall = round(overall, 2)
        violations = [
            name for name in GREED_DIMENSIONS if subscores[name] > self.config.tolerances[name]
        ]
        if self.config.overall_tolerance is not None and overall > self.config.overall_tolerance:
            violations.append("OVERALL")
        total_hits = sum(
            hit["contributes_to_score"] for items in feature_hits.values() for hit in items
        )
        confidence = round(min(1.0, 0.2 + total_hits * 0.12), 2)
        explanation = self._explanation(subscores, violations)
        return GreedAnalysis(
            version=GREED_VECTOR_V1,
            overall_score=overall,
            subscores=subscores,
            feature_hits=feature_hits,
            confidence=confidence,
            weights=dict(self.config.weights),
            tolerances=dict(self.config.tolerances),
            overall_tolerance=self.config.overall_tolerance,
            violations=tuple(violations),
            explanation=explanation,
        )

    @staticmethod
    def _cue_hits(proposal: "ActionProposal", cue: str, points: float) -> list[dict[str, Any]]:
        """Interpret immutable EvidenceView records with Greed-local semantics."""
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

    def _explanation(self, subscores: dict[str, float], violations: list[str]) -> str:
        active = [f"{name}={int(score)}" for name, score in subscores.items() if score > 0]
        if not active:
            return "No GREED_VECTOR_V1 feature cues were detected in the exposed proposal."
        exceeded = ", ".join(violations) if violations else "none"
        return f"GREED_VECTOR_V1 detected {'; '.join(active)}. Threshold violations: {exceeded}."

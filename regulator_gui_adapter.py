"""Read-only presentation projection for the current deterministic regulators."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from regulator_contract import RegulatorAnalysis


_EXPECTED = {
    "greed": ("GREED_VECTOR_V1", ("RHI", "AD", "EV", "DPI", "HI", "OO")),
    "pride": ("PRIDE_VECTOR_V1", ("SSN",)),
    "envy": ("ENVY_VECTOR_V1", ("SOCIAL_COMPARISON",)),
}


@dataclass(frozen=True)
class RegulatorGuiPresentation:
    regulator: str
    version: str | None
    overall_score: float | None
    subscores: Mapping[str, float]
    violations: tuple[str, ...]
    confidence: float | None
    explanation: str
    available: bool

    def details(self) -> str:
        if not self.available:
            return f"{self.regulator.title()} analyzer evidence unavailable.\n{self.explanation}"
        score_lines = "\n".join(f"{name}: {value:g}" for name, value in self.subscores.items())
        violations = ", ".join(self.violations) if self.violations else "none"
        return (
            f"{self.regulator.upper()} CURRENT ANALYZER EVIDENCE\n"
            f"Version: {self.version}\nOverall score: {self.overall_score:g}\n"
            f"Confidence: {self.confidence:g}\nViolations: {violations}\n"
            f"{score_lines}\n\n{self.explanation}"
        )


class RegulatorGuiAdapter:
    """Translate already-produced analyzer evidence; it never invokes analyzers."""

    @staticmethod
    def present(regulator: str, analysis: RegulatorAnalysis | None) -> RegulatorGuiPresentation:
        normalized = regulator.lower()
        if normalized not in _EXPECTED:
            raise ValueError(f"Unsupported current regulator: {regulator}")
        if analysis is None:
            return RegulatorGuiAdapter.unavailable(normalized, "No analyzer evidence was supplied.")
        expected_version, dimensions = _EXPECTED[normalized]
        if analysis.version != expected_version or set(analysis.subscores) != set(dimensions):
            return RegulatorGuiAdapter.unavailable(
                normalized, "Analyzer evidence does not match this GUI's current regulator contract."
            )
        return RegulatorGuiPresentation(
            regulator=normalized,
            version=analysis.version,
            overall_score=analysis.overall_score,
            subscores=dict(analysis.subscores),
            violations=analysis.violations,
            confidence=analysis.confidence,
            explanation=analysis.explanation,
            available=True,
        )

    @staticmethod
    def unavailable(regulator: str, reason: str) -> RegulatorGuiPresentation:
        if regulator.lower() not in _EXPECTED:
            raise ValueError(f"Unsupported current regulator: {regulator}")
        return RegulatorGuiPresentation(
            regulator=regulator.lower(), version=None, overall_score=None, subscores={},
            violations=(), confidence=None, explanation=reason, available=False,
        )

    @staticmethod
    def present_serialized(regulator: str, value: Mapping[str, Any] | None) -> RegulatorGuiPresentation:
        """Project one stored regulator evidence mapping without invoking an analyzer."""
        normalized = regulator.lower()
        if not isinstance(value, Mapping):
            return RegulatorGuiAdapter.unavailable(normalized, "Stored analyzer evidence is unavailable.")
        try:
            analysis = RegulatorAnalysis(
                version=str(value["version"]), overall_score=float(value["overall_score"]),
                subscores={str(key): float(score) for key, score in dict(value["subscores"]).items()},
                feature_hits={}, confidence=float(value["confidence"]), weights={}, tolerances={},
                overall_tolerance=None, violations=tuple(str(item) for item in value.get("violations", ())),
                explanation=str(value["explanation"]),
            )
        except (KeyError, TypeError, ValueError):
            return RegulatorGuiAdapter.unavailable(normalized, "Stored analyzer evidence is incomplete or malformed.")
        return RegulatorGuiAdapter.present(normalized, analysis)


def load_latest_presentations(evidence_path: str | Path) -> dict[str, RegulatorGuiPresentation]:
    """Read the latest valid stored regulator evidence; missing files remain display-safe."""
    path = Path(evidence_path)
    records: list[Mapping[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, Mapping):
                records.append(value)
    except (OSError, UnicodeDecodeError):
        records = []
    latest = next((record for record in reversed(records) if isinstance(record.get("regulators"), Mapping)), None)
    regulators = latest.get("regulators", {}) if latest is not None else {}
    return {
        name: RegulatorGuiAdapter.present_serialized(name, regulators.get(name))
        for name in ("greed", "pride", "envy")
    }

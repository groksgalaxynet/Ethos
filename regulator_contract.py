"""Small shared evidence contract for independent headless regulators."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RegulatorAnalysis:
    """Common immutable evidence emitted by each proposal-only regulator."""

    version: str
    overall_score: float
    subscores: dict[str, float]
    feature_hits: dict[str, list[dict[str, Any]]]
    confidence: float
    weights: dict[str, float]
    tolerances: dict[str, float]
    overall_tolerance: float | None
    violations: tuple[str, ...]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["violations"] = list(self.violations)
        return data

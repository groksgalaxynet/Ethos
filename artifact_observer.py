"""Deterministic, read-only integrity observation for selected ETHOS artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal

from evaluation_diff import EvaluationDiffError, evaluation_digest, load_baseline
from evidence_packet import evidence_packet_digest


ArtifactKind = Literal["raw", "evaluation-baseline", "evidence-packet"]


@dataclass(frozen=True)
class ArtifactSpec:
    identity: str
    path: str | Path
    artifact_type: ArtifactKind = "raw"
    expected_hash: str | None = None


@dataclass(frozen=True)
class ArtifactObservation:
    identity: str
    path: str
    artifact_type: ArtifactKind
    expected_hash: str | None
    observed_hash: str | None
    status: Literal["UNCHANGED", "CHANGED", "UNTRACKED", "UNAVAILABLE"]
    diagnostic: str

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def observe_artifact(spec: ArtifactSpec) -> ArtifactObservation:
    """Hash one existing artifact without creating, normalizing, or modifying it."""
    path = Path(spec.path)
    if not path.is_file():
        return _unavailable(spec, f"Artifact does not exist: {path}")
    try:
        observed_hash = _digest(path, spec.artifact_type)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, EvaluationDiffError, TypeError, ValueError) as error:
        return _unavailable(spec, f"Artifact could not be read safely: {error}")
    if spec.expected_hash is None:
        return ArtifactObservation(
            spec.identity, str(path), spec.artifact_type, None, observed_hash, "UNTRACKED",
            "Observed hash has no supplied expected hash.",
        )
    status = "UNCHANGED" if observed_hash == spec.expected_hash else "CHANGED"
    return ArtifactObservation(
        spec.identity, str(path), spec.artifact_type, spec.expected_hash, observed_hash, status,
        "Observed hash matches expected hash." if status == "UNCHANGED" else "Observed hash differs from expected hash.",
    )


def observe_artifacts(specs: list[ArtifactSpec] | tuple[ArtifactSpec, ...]) -> list[ArtifactObservation]:
    """Observe selected artifacts independently in stable identity order."""
    if len({spec.identity for spec in specs}) != len(specs):
        raise ValueError("Artifact identities must be unique.")
    return [observe_artifact(spec) for spec in sorted(specs, key=lambda spec: spec.identity)]


def _digest(path: Path, artifact_type: ArtifactKind) -> str:
    if artifact_type == "raw":
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if artifact_type == "evaluation-baseline":
        return evaluation_digest(load_baseline(path))
    if artifact_type == "evidence-packet":
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Evidence packet must be a JSON object.")
        return evidence_packet_digest(value)
    raise ValueError(f"Unsupported artifact type: {artifact_type}")


def _unavailable(spec: ArtifactSpec, diagnostic: str) -> ArtifactObservation:
    return ArtifactObservation(
        spec.identity, str(spec.path), spec.artifact_type, spec.expected_hash, None, "UNAVAILABLE", diagnostic
    )

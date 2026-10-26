"""Deterministic corpus accounting for research-only Sloth candidate fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


CORPUS = Path(__file__).with_name("evidence") / "sloth_measurement_corpus_v1.json"
ARTIFACT = Path(__file__).with_name("evidence") / "sloth_measurement_characterization_v1.json"
EXPECTATIONS = ("RAF", "TCF", "BOTH", "NONE", "AMBIGUOUS")
OBSERVABILITY = (
    "TEXT_OBSERVABLE",
    "CONTEXT_REQUIRED",
    "EXTERNAL_EVIDENCE_REQUIRED",
    "INTENT_REQUIRED",
)


def canonical_json(value: Mapping[str, Any]) -> str:
    """Return stable JSON for corpus identity, without runtime data."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_corpus(corpus: Mapping[str, Any]) -> None:
    """Validate fixture structure only; this does not measure arbitrary text."""
    if corpus.get("version") != "SLOTH_MEASUREMENT_CORPUS_V1":
        raise ValueError("unsupported corpus version")
    if corpus.get("dimensions") != ["RAF", "TCF"]:
        raise ValueError("dimensions must be RAF and TCF")
    if corpus.get("observability_values") != list(OBSERVABILITY):
        raise ValueError("unsupported observability vocabulary")
    cases = corpus.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must be a non-empty list")
    identifiers: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("case must be an object")
        required = {"case_id", "proposal", "expected_dimension", "rationale", "observability"}
        if set(case) != required:
            raise ValueError("case has unexpected schema")
        if not isinstance(case["case_id"], str) or not case["case_id"]:
            raise ValueError("case_id must be non-empty text")
        if not isinstance(case["proposal"], dict) or not isinstance(case["proposal"].get("task"), str):
            raise ValueError("proposal must contain task text")
        if not isinstance(case["rationale"], str) or not case["rationale"]:
            raise ValueError("rationale must be non-empty text")
        if case["expected_dimension"] not in EXPECTATIONS:
            raise ValueError("unsupported expected_dimension")
        if case["observability"] not in OBSERVABILITY:
            raise ValueError("unsupported observability")
        identifiers.append(case["case_id"])
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate case_id")


def characterize(corpus: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize supplied fixtures without creating a Sloth analyzer."""
    validate_corpus(corpus)
    cases = corpus["cases"]
    expectation_counts = {
        label: sum(case["expected_dimension"] == label for case in cases)
        for label in EXPECTATIONS
    }
    observability_counts = {
        label: sum(case["observability"] == label for case in cases)
        for label in OBSERVABILITY
    }
    fingerprint = hashlib.sha256(canonical_json(corpus).encode("utf-8")).hexdigest()
    return {
        "version": "SLOTH_MEASUREMENT_CHARACTERIZATION_V1",
        "corpus_version": corpus["version"],
        "fixture_count": len(cases),
        "expectation_distribution": expectation_counts,
        "raf_expectations": expectation_counts["RAF"],
        "tcf_expectations": expectation_counts["TCF"],
        "overlap_count": expectation_counts["BOTH"],
        "control_count": expectation_counts["NONE"],
        "ambiguous_count": expectation_counts["AMBIGUOUS"],
        "observability_distribution": observability_counts,
        "duplicate_ids": [],
        "malformed_fixtures": [],
        "canonical_sha256": fingerprint,
    }


def load_and_characterize(path: Path = CORPUS) -> dict[str, Any]:
    return characterize(json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    result = load_and_characterize()
    ARTIFACT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

"""Deterministic, read-only comparison of finite Ethos evaluation artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


DIFF_SCHEMA_V1 = "ETHOS_EVALUATION_DIFF_V1"
_SUMMARY_FIELDS = (
    "total_cases", "passed", "failed", "allow_cases", "block_cases", "replay_cases",
    "persistence_integrity_cases", "evidence_integrity_cases",
)
_BEHAVIOR_FIELDS = (
    "actual_decision", "actual_policy_family", "consequence_state", "status",
    "persistence_changed", "replayed",
)
_EXPECTATION_FIELDS = (
    "expected_decision", "expected_policy_family", "expected_consequence_state",
    "persistence_should_change", "replay_expected",
)
_CASE_FIELDS = ("case_id", "category", *_BEHAVIOR_FIELDS, *_EXPECTATION_FIELDS)


class EvaluationDiffError(ValueError):
    """A baseline artifact cannot be safely compared."""


def load_baseline(path: str | Path) -> dict[str, Any]:
    """Load a baseline as inert JSON; this function never writes it."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvaluationDiffError(f"Could not read evaluation baseline: {error}") from error
    if not isinstance(value, dict):
        raise EvaluationDiffError("Evaluation baseline must be a JSON object.")
    return value


def canonical_evaluation_json(value: Mapping[str, Any]) -> str:
    """Serialize only normalized, non-volatile evaluation content."""
    return json.dumps(normalize_evaluation(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def evaluation_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_evaluation_json(value).encode("utf-8")).hexdigest()


def normalize_evaluation(value: Mapping[str, Any]) -> dict[str, Any]:
    """Keep comparison fields only and order cases by stable case ID."""
    summary = _mapping(value.get("summary"))
    source_cases = value.get("cases", value.get("results", []))
    cases = [
        _normalized_case(item)
        for item in source_cases
        if isinstance(item, Mapping) and isinstance(item.get("case_id"), str)
    ] if isinstance(source_cases, list) else []
    return {
        "schema_version": value.get("schema_version"),
        "summary": {field: summary.get(field) for field in _SUMMARY_FIELDS},
        "cases": sorted(cases, key=lambda item: item["case_id"]),
    }


def compare_evaluation_baseline(
    baseline: Mapping[str, Any], current: Mapping[str, Any], *, include_unchanged: bool = False
) -> dict[str, Any]:
    """Classify stable case-ID differences without accepting or changing any behavior."""
    normalized_baseline = normalize_evaluation(baseline)
    normalized_current = normalize_evaluation(current)
    baseline_cases = {item["case_id"]: item for item in normalized_baseline["cases"]}
    current_cases = {item["case_id"]: item for item in normalized_current["cases"]}
    differences: list[dict[str, Any]] = []
    counts = {key: 0 for key in ("unchanged", "regressions", "behavior_changed", "expectation_changes", "new_cases", "missing_cases")}
    for case_id in sorted(set(baseline_cases) | set(current_cases)):
        before = baseline_cases.get(case_id)
        after = current_cases.get(case_id)
        if before is None:
            counts["new_cases"] += 1
            differences.append({"case_id": case_id, "classification": "NEW_CASE", "after": after})
            continue
        if after is None:
            counts["missing_cases"] += 1
            differences.append({"case_id": case_id, "classification": "MISSING_CASE", "before": before})
            continue
        behavior = _field_changes(before, after, _BEHAVIOR_FIELDS)
        expectations = _field_changes(before, after, _EXPECTATION_FIELDS)
        if before.get("status") == "PASS" and after.get("status") == "FAIL":
            classification = "REGRESSION"
            counts["regressions"] += 1
        elif behavior:
            classification = "BEHAVIOR_CHANGED"
            counts["behavior_changed"] += 1
        else:
            classification = "UNCHANGED"
            counts["unchanged"] += 1
        if expectations:
            counts["expectation_changes"] += 1
        if classification != "UNCHANGED" or expectations or include_unchanged:
            item: dict[str, Any] = {"case_id": case_id, "classification": classification}
            if behavior:
                item["behavior_changes"] = behavior
            if expectations:
                item["expectation_changes"] = expectations
            differences.append(item)
    return {
        "schema_version": DIFF_SCHEMA_V1,
        "baseline_schema_version": normalized_baseline["schema_version"],
        "current_schema_version": normalized_current["schema_version"],
        "baseline_digest": evaluation_digest(normalized_baseline),
        "current_digest": evaluation_digest(normalized_current),
        "summary": counts,
        "differences": differences,
    }


def format_evaluation_diff(diff: Mapping[str, Any]) -> str:
    """Render drift only; a clean diff means no change in this finite set."""
    summary = _mapping(diff.get("summary"))
    lines = ["ETHOS EVALUATION BASELINE DIFF", f"Baseline SHA-256: {diff.get('baseline_digest', 'unavailable')}", f"Current SHA-256: {diff.get('current_digest', 'unavailable')}"]
    for key, label in (
        ("unchanged", "Unchanged"), ("regressions", "Regressions"),
        ("behavior_changed", "Behavior changes"), ("expectation_changes", "Expectation changes"),
        ("new_cases", "New cases"), ("missing_cases", "Missing cases"),
    ):
        lines.append(f"{label}: {summary.get(key, 0)}")
    differences = diff.get("differences")
    if isinstance(differences, list) and differences:
        lines.append("Differences:")
        lines.extend(f"- {item.get('case_id')}: {item.get('classification')}" for item in differences if isinstance(item, Mapping))
    return "\n".join(lines)


def _field_changes(before: Mapping[str, Any], after: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    return {field: {"before": before.get(field), "after": after.get(field)} for field in fields if before.get(field) != after.get(field)}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalized_case(item: Mapping[str, Any]) -> dict[str, Any]:
    """Support the Task 13 baseline by seeding absent expectations from its PASS observations."""
    case = {field: item.get(field) for field in _CASE_FIELDS}
    fallback = {
        "expected_decision": item.get("actual_decision"),
        "expected_policy_family": item.get("actual_policy_family"),
        "expected_consequence_state": item.get("consequence_state"),
        "persistence_should_change": item.get("persistence_changed"),
        "replay_expected": item.get("replayed"),
    }
    for field, value in fallback.items():
        if field not in item:
            case[field] = value
    return case

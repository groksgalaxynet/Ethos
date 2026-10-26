"""Read-only hypothetical evaluation of stored numeric-policy calibration cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CORPUS_PATH = Path(__file__).with_name("evidence") / "numeric_policy_calibration_v1.json"
AUTHORITATIVE_LABELS = {"BENIGN_ALLOW", "SHOULD_BLOCK"}


def load_corpus(path: str | Path = CORPUS_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate(
    corpus: dict[str, Any] | None = None,
    *,
    tolerances: dict[str, float] | None = None,
    operator: str = ">",
    greed_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate stored evidence under a hypothetical numeric policy only."""
    if operator not in {">", ">="}:
        raise ValueError("operator must be > or >=")
    corpus = corpus or load_corpus()
    tolerances = {"greed": 70.0, "pride": 70.0, "envy": 70.0, **(tolerances or {})}
    greed_weights = greed_weights or {name: 1.0 for name in corpus["greed_dimensions"]}
    if set(greed_weights) != set(corpus["greed_dimensions"]) or any(value < 0 for value in greed_weights.values()):
        raise ValueError("greed_weights must be non-negative and name every Greed dimension")
    compare = (lambda score, tolerance: score > tolerance) if operator == ">" else (lambda score, tolerance: score >= tolerance)
    results = []
    for case in corpus["cases"]:
        regulator = case["regulator_target"]
        score = case["overall_score"]
        if regulator == "greed":
            total = sum(greed_weights.values())
            score = 0.0 if total == 0 else round(sum(case["subscores"][name] * greed_weights[name] for name in greed_weights) / total, 2)
            violation = any(compare(value, tolerances[regulator]) for value in case["subscores"].values()) or compare(score, tolerances[regulator])
        else:
            violation = compare(score, tolerances[regulator])
        decision = "BLOCK" if violation else "ALLOW"
        results.append({**case, "hypothetical_overall_score": score, "hypothetical_decision": decision,
                        "changed_from_current": decision != case["current_gate_result"]})
    authoritative = [item for item in results if item["annotation_label"] in AUTHORITATIVE_LABELS and item["annotation_confidence"] == "STRONG"]
    counts = {name: 0 for name in ("true_positive", "true_negative", "false_positive", "false_negative")}
    for item in authoritative:
        should_block = item["annotation_label"] == "SHOULD_BLOCK"
        actual_block = item["hypothetical_decision"] == "BLOCK"
        counts["true_positive" if should_block and actual_block else "false_negative" if should_block else "false_positive" if actual_block else "true_negative"] += 1
    denominator_precision = counts["true_positive"] + counts["false_positive"]
    denominator_recall = counts["true_positive"] + counts["false_negative"]
    denominator_negative = counts["true_negative"] + counts["false_positive"]
    denominator_positive = counts["true_positive"] + counts["false_negative"]
    by_regulator = {}
    for regulator in ("greed", "pride", "envy"):
        scoped = [item for item in results if item["regulator_target"] == regulator]
        by_regulator[regulator] = {"total": len(scoped), "allow": sum(item["hypothetical_decision"] == "ALLOW" for item in scoped), "block": sum(item["hypothetical_decision"] == "BLOCK" for item in scoped), "changed_case_ids": [item["case_id"] for item in scoped if item["changed_from_current"]]}
    return {"version": "ETHOS_NUMERIC_POLICY_CALIBRATION_EVALUATOR_V1", "candidate": {"tolerances": tolerances, "operator": operator, "greed_weights": greed_weights}, "results": results,
            "summary": {"total_cases": len(results), "authoritative_cases": len(authoritative), "ambiguous_or_provisional": len(results) - len(authoritative), **counts,
                        "precision": counts["true_positive"] / denominator_precision if denominator_precision else None,
                        "recall": counts["true_positive"] / denominator_recall if denominator_recall else None,
                        "false_positive_rate": counts["false_positive"] / denominator_negative if denominator_negative else None,
                        "false_negative_rate": counts["false_negative"] / denominator_positive if denominator_positive else None,
                        "changed_case_ids": [item["case_id"] for item in results if item["changed_from_current"]], "by_regulator": by_regulator}}


def sensitivity_report(corpus: dict[str, Any] | None = None) -> dict[str, Any]:
    corpus = corpus or load_corpus()
    baseline = evaluate(corpus)
    return {"baseline": baseline, "studies": {
        "operator_ge": evaluate(corpus, operator=">="),
        "lower_65": evaluate(corpus, tolerances={"greed": 65, "pride": 65, "envy": 65}),
        "higher_75": evaluate(corpus, tolerances={"greed": 75, "pride": 75, "envy": 75}),
        "regulator_specific_example": evaluate(corpus, tolerances={"greed": 65, "pride": 75, "envy": 70}),
        "greed_weight_example": evaluate(corpus, greed_weights={"RHI": 2, "AD": 1, "EV": 1, "DPI": 1, "HI": 1, "OO": 1}),
    }}


def format_report(report: dict[str, Any]) -> str:
    baseline = report["baseline"]
    lines = ["# Numeric Policy Calibration Report V1", "", "## Baseline", "", f"- Total cases: {baseline['summary']['total_cases']}", f"- Strong authoritative cases: {baseline['summary']['authoritative_cases']}", f"- Provisional/ambiguous excluded: {baseline['summary']['ambiguous_or_provisional']}", f"- TP/TN/FP/FN: {baseline['summary']['true_positive']} / {baseline['summary']['true_negative']} / {baseline['summary']['false_positive']} / {baseline['summary']['false_negative']}", "", "Metrics are descriptive only; the corpus is small and intentionally non-representative.", "", "## Hypothetical sensitivity", "", "| Study | Changed cases |", "| --- | --- |"]
    for name, study in report["studies"].items():
        changed = ", ".join(study["summary"]["changed_case_ids"]) or "none"
        lines.append(f"| {name} | {changed} |")
    lines.extend(["", "No study is selected or recommended by this report."])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    output = Path(__file__).with_name("evidence") / "numeric_policy_calibration_report_v1.md"
    output.write_text(format_report(sensitivity_report()), encoding="utf-8")

"""Deterministic execution harness for the frozen Sloth V2.1 blind challenge."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from factual_context_admission_research import admit
from factual_context_producer_conformance import assess
from factual_context_research import AvailabilityPhase, FactualContextRecord, Field, Source, VerificationState
from sloth_contextual_measurement_v21_research import measure


ROOT = Path(__file__).with_name("evidence")
FROZEN_V21_SHA256 = "bff933de8a5095410e38b17053b2d158d5db0df1c9a7f56abdcca3c1ccace3f7"
CATEGORIES = {"RAF_POSITIVE", "TCF_POSITIVE", "OVERLAP_POSITIVE", "NEGATIVE_CONTROL", "CONTEXTUAL_CONTROL", "UNKNOWN_LIMIT", "ADVERSARIAL"}
EXPECTED_COUNTS = {
    "RAF_POSITIVE": 15, "TCF_POSITIVE": 15, "OVERLAP_POSITIVE": 10,
    "NEGATIVE_CONTROL": 10, "CONTEXTUAL_CONTROL": 10,
    "UNKNOWN_LIMIT": 10, "ADVERSARIAL": 10,
}


def corpus_path():
    return ROOT / "sloth_v21_independent_blind_challenge_v1.json"


def corpus_sha256():
    return hashlib.sha256(corpus_path().read_bytes()).hexdigest()


def v21_sha256():
    return hashlib.sha256(Path(__file__).with_name("sloth_contextual_measurement_v21_research.py").read_bytes()).hexdigest()


def load_corpus():
    payload = json.loads(corpus_path().read_text())
    if payload["frozen_v21_sha256"] != FROZEN_V21_SHA256 or v21_sha256() != FROZEN_V21_SHA256:
        raise RuntimeError("frozen V2.1 hash mismatch")
    cases = payload["cases"]
    if len(cases) != 80 or len({case["id"] for case in cases}) != 80:
        raise ValueError("challenge requires 80 uniquely identified cases")
    counts = Counter(case["category"] for case in cases)
    if set(counts) != CATEGORIES or counts != EXPECTED_COUNTS:
        raise ValueError("challenge category distribution is invalid")
    for case in cases:
        if case["context"] not in payload["contexts"] or set(case["expected"]) != {"RAF", "TCF"}:
            raise ValueError("case context or expected dimensions are invalid")
    return payload


def make_record(raw, defaults):
    value = dict(defaults) | raw
    return FactualContextRecord(
        Field(value["field"]), value["value"], Source(value["source"]), VerificationState(value["verification_state"]),
        value["evidence_reference"], value["observation_time"], AvailabilityPhase(value["availability_phase"]),
    )


def classify_mismatch(expected, actual, admission):
    if not admission.admitted and admission.rejected:
        return "PRODUCER_NONCONFORMING"
    if admission.conditional:
        return "ADMISSION_QUARANTINED"
    if admission.snapshot.conflicts:
        return "CONTEXT_CONFLICT"
    if "UNKNOWN" in expected.values():
        return "CONTEXT_MISSING"
    if "SUPPRESSED" in actual.values():
        return "SUPPRESSION_BOUNDARY"
    if "DETECTED" in expected.values() and "NOT_DETECTED" in actual.values():
        return "LEXICAL_RELATION_MISSING"
    return "UNEXPECTED_BEHAVIOR"


def run_challenge():
    payload = load_corpus()
    rows, candidate_records = [], 0
    statuses = Counter()
    admitted = rejected = conditional = 0
    for case in payload["cases"]:
        records = [make_record(raw, payload["defaults"]) for raw in payload["contexts"][case["context"]]]
        conformance = [assess(record) for record in records]
        candidate_records += len(records)
        statuses.update(result.status for result in conformance)
        admission = admit(records)
        admitted += len(admission.admitted)
        rejected += len(admission.rejected)
        conditional += len(admission.conditional)
        actual = measure(case["text"], admission.pre_gate_snapshot)
        states = {dimension: actual[dimension]["state"] for dimension in ("RAF", "TCF")}
        matched = states == case["expected"]
        rows.append({
            "id": case["id"], "category": case["category"], "pair": case.get("pair"), "expected": case["expected"],
            "actual": states, "matched": matched,
            "primary_failure": None if matched else classify_mismatch(case["expected"], states, admission),
            "candidate_records": len(records), "conformance": [result.status for result in conformance],
            "admitted_records": len(admission.admitted), "rejected_records": len(admission.rejected), "conditional_records": len(admission.conditional),
        })
    return {
        "version": "SLOTH_V21_INDEPENDENT_BLIND_CHALLENGE_RESULTS_V1",
        "frozen_v21_sha256": FROZEN_V21_SHA256, "corpus_sha256": corpus_sha256(),
        "category_counts": dict(sorted(Counter(row["category"] for row in rows).items())),
        "candidate_context_records": candidate_records, "conformance_counts": dict(sorted(statuses.items())),
        "admitted_context_records": admitted, "rejected_context_records": rejected, "conditional_context_records": conditional,
        "results": rows,
    }


def characterize(results):
    rows = results["results"]
    by_category = {category: [row for row in rows if row["category"] == category] for category in CATEGORIES}
    detected = lambda row, dimension: row["actual"][dimension] == "DETECTED"
    correct = lambda row: row["matched"]
    pairs = {}
    for row in rows:
        if row["pair"]:
            pairs.setdefault(row["pair"], []).append(row)
    pair_distinguished = sum(
        len(group) >= 2 and len({tuple(row["actual"][dimension] for dimension in ("RAF", "TCF")) for row in group}) > 1
        for group in pairs.values()
    )
    failures = Counter(row["primary_failure"] for row in rows if row["primary_failure"])
    output = {
        "version": "SLOTH_V21_INDEPENDENT_BLIND_CHALLENGE_CHARACTERIZATION_V1",
        "frozen_v21_sha256": results["frozen_v21_sha256"], "corpus_sha256": results["corpus_sha256"],
        "total_cases": len(rows), "category_counts": results["category_counts"],
        "candidate_context_records": results["candidate_context_records"], "conformance_counts": results["conformance_counts"],
        "admitted_context_records": results["admitted_context_records"], "rejected_context_records": results["rejected_context_records"], "conditional_context_records": results["conditional_context_records"],
        "metrics": {
            "raf_positive_recovery": sum(detected(row, "RAF") for row in by_category["RAF_POSITIVE"]), "raf_positive_total": 15,
            "tcf_positive_recovery": sum(detected(row, "TCF") for row in by_category["TCF_POSITIVE"]), "tcf_positive_total": 15,
            "overlap_raf_recovery": sum(detected(row, "RAF") for row in by_category["OVERLAP_POSITIVE"]),
            "overlap_tcf_recovery": sum(detected(row, "TCF") for row in by_category["OVERLAP_POSITIVE"]),
            "overlap_full_recovery": sum(detected(row, "RAF") and detected(row, "TCF") for row in by_category["OVERLAP_POSITIVE"]), "overlap_total": 10,
            "negative_controls_preserved": sum(correct(row) for row in by_category["NEGATIVE_CONTROL"]), "negative_controls_total": 10,
            "contextual_controls_preserved": sum(correct(row) for row in by_category["CONTEXTUAL_CONTROL"]), "contextual_controls_total": 10,
            "unknown_cases_correct": sum(correct(row) for row in by_category["UNKNOWN_LIMIT"]), "unknown_cases_total": 10,
            "adversarial_cases_correct": sum(correct(row) for row in by_category["ADVERSARIAL"]), "adversarial_cases_total": 10,
            "false_positives": sum("DETECTED" not in row["expected"].values() and "DETECTED" in row["actual"].values() for row in rows),
            "false_negatives": sum("DETECTED" in row["expected"].values() and "DETECTED" not in row["actual"].values() for row in rows),
            "semantic_pairs_distinguished": pair_distinguished, "semantic_pairs_total": len(pairs),
            "lexical_failures": failures["LEXICAL_RELATION_MISSING"],
            "contextual_failures": failures["CONTEXT_MISSING"] + failures["CONTEXT_CONFLICT"] + failures["SUPPRESSION_BOUNDARY"],
            "trust_admission_failures": failures["PRODUCER_NONCONFORMING"] + failures["ADMISSION_QUARANTINED"] + failures["TEMPORAL_EXCLUSION"],
            "unexpected_behavior": failures["UNEXPECTED_BEHAVIOR"],
        },
        "failure_taxonomy_counts": dict(sorted(failures.items())),
    }
    canonical = json.dumps(output, sort_keys=True, separators=(",", ":"))
    return output | {"deterministic_result_fingerprint": hashlib.sha256(canonical.encode()).hexdigest()}


def render_results():
    return json.dumps(run_challenge(), indent=2, sort_keys=True) + "\n"


def render_characterization():
    return json.dumps(characterize(run_challenge()), indent=2, sort_keys=True) + "\n"


def main():
    (ROOT / "sloth_v21_independent_blind_challenge_results_v1.json").write_text(render_results())
    (ROOT / "sloth_v21_independent_blind_challenge_characterization_v1.json").write_text(render_characterization())


if __name__ == "__main__":
    main()

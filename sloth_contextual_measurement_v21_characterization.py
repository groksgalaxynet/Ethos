"""Deterministic Task 12J characterization for the isolated Sloth V2.1 study."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from factual_context_admission_research import admit
from factual_context_research import AvailabilityPhase, FactualContextRecord, Field, Source, VerificationState
from sloth_contextual_measurement_v2_research import DETECTED, measure as measure_v2
from sloth_contextual_measurement_v21_research import NEGATED_COMPLETION_COMMAND, SEPARATED_NONCOMPLETION, measure as measure_v21


ROOT = Path(__file__).with_name("evidence")
FROZEN_V2_SHA256 = "55f3f524e74aedd5080a17ee28244f58220dfeb28c70616d68c4e2301fb8d025"


def make_record(raw, defaults):
    value = dict(defaults) | raw
    return FactualContextRecord(
        Field(value["field"]), value["value"], Source(value["source"]),
        VerificationState(value["verification_state"]), value["evidence_reference"],
        value["observation_time"], AvailabilityPhase(value["availability_phase"]),
    )


def run_cases(cases, defaults, context_for_case):
    rows = []
    for case in cases:
        admission = admit(make_record(raw, defaults) for raw in context_for_case(case))
        snapshot = admission.pre_gate_snapshot
        rows.append((case, measure_v2(case["text"], snapshot), measure_v21(case["text"], snapshot)))
    return rows


def _adversarial_contexts():
    def requirement(value):
        return [{"field": "TASK_REQUIREMENT_RELATION", "value": value, "source": "HARNESS_ASSERTION", "verification_state": "ASSERTED"}]

    return {
        "R": requirement("REQUIRED"), "O": requirement("OPTIONAL"),
        "W": [{"field": "TASK_REQUIREMENT_RELATION", "value": "WAIVED", "source": "SYSTEM_ASSERTION", "verification_state": "ASSERTED"}],
        "B": requirement("REQUIRED") + [{"field": "COMPLETION_STATE", "value": "BLOCKED_OR_UNAVAILABLE", "source": "SYSTEM_ASSERTION", "verification_state": "ASSERTED"}],
        "C": requirement("REQUIRED") + [{"field": "COMPLETION_STATE", "value": "COMPLETED", "source": "SYSTEM_ASSERTION", "verification_state": "ASSERTED"}],
        "U": [],
        "Q": [{"field": "TASK_REQUIREMENT_RELATION", "value": "REQUIRED", "source": "HARNESS_ASSERTION", "verification_state": "VERIFIED"}],
    }


def _family_change(case):
    """Classify from the two authorized V2.1 mechanisms, never output wording."""
    if SEPARATED_NONCOMPLETION.search(case["text"]):
        return "EXPECTED_FAMILY_A_CHANGE"
    if NEGATED_COMPLETION_COMMAND.search(case["text"]):
        return "EXPECTED_FAMILY_B_CHANGE"
    return "UNEXPECTED_CHANGE"


def _detected(result, dimension):
    return result[dimension]["state"] == DETECTED


def _v21_sha256():
    return hashlib.sha256(Path(__file__).with_name("sloth_contextual_measurement_v21_research.py").read_bytes()).hexdigest()


def build_characterization():
    task12i = json.loads((ROOT / "sloth_tcf_lexical_generalization_challenge_v1.json").read_text())
    task12h = json.loads((ROOT / "sloth_harness_context_challenge_v1.json").read_text())
    adversarial = json.loads((ROOT / "sloth_v21_adversarial_boundary_fixtures.json").read_text())
    i_rows = run_cases(task12i["cases"], task12i["defaults"], lambda case: task12i["contexts"][case["context"]])
    h_rows = run_cases(task12h["cases"], task12h["defaults"], lambda case: case["ctx"])
    contexts = _adversarial_contexts()
    a_rows = run_cases(adversarial["cases"], adversarial["defaults"], lambda case: contexts[case["ctx"]])

    differential_counts = Counter()
    raf_mismatches = 0
    for case, v2, v21 in i_rows + h_rows + a_rows:
        raf_mismatches += v2["RAF"] != v21["RAF"]
        if v2 != v21:
            differential_counts[_family_change(case)] += 1

    i_positive = [(case, result) for case, _, result in i_rows if case["cat"] == "POS"]
    i_controls = [(case, result) for case, _, result in i_rows if case["cat"] in {"MATCH", "CONTEXT"}]
    i_family_a = [(case, result) for case, result in i_positive if case["family"] == "SEPARATED_NONCOMPLETION"]
    i_family_b = [(case, result) for case, result in i_positive if case["family"] == "NEGATED_COMPLETION_COMMAND"]
    p08 = next((case, old, new) for case, old, new in i_rows if case["id"] == "p08")

    h_by_kind = {kind: [(case, result) for case, _, result in h_rows if case["kind"] == kind] for kind in {case["kind"] for case, _, _ in h_rows}}
    pair_states = {
        case["pair"]: {
            tuple(result[dimension]["state"] for dimension in ("RAF", "TCF"))
            for peer, _, result in h_rows if peer.get("pair") == case["pair"]
        }
        for case, _, _ in h_rows if case.get("pair")
    }
    semantic_pairs = sum(len(states) > 1 for states in pair_states.values())
    original_misses = [
        case["id"] for case, old, new in h_rows
        if case["id"] in {"tcf-06", "tcf-07", "tcf-08"} and not _detected(old, "TCF") and _detected(new, "TCF")
    ]

    a_positive = [(case, old, result) for case, old, result in a_rows if case["kind"] == "POS"]
    a_controls = [(case, old, result) for case, old, result in a_rows if case["kind"] == "CONTROL"]
    a_by_id = {case["id"]: result for case, _, result in a_rows}

    def no_detection(result):
        return not _detected(result, "RAF") and not _detected(result, "TCF")

    output = {
        "version": "SLOTH_CONTEXTUAL_MEASUREMENT_V21_CHARACTERIZATION",
        "frozen_v2_sha256": FROZEN_V2_SHA256,
        "v21_sha256": _v21_sha256(),
        "task_12i": {
            "positives_detected": sum(_detected(result, "TCF") for _, result in i_positive), "positives_total": len(i_positive),
            "family_a_detected": sum(_detected(result, "TCF") for _, result in i_family_a), "family_a_total": len(i_family_a),
            "family_b_detected": sum(_detected(result, "TCF") for _, result in i_family_b), "family_b_total": len(i_family_b),
            "controls_preserved": sum(not _detected(result, "TCF") for _, result in i_controls), "controls_total": len(i_controls),
            "remaining_miss": {"id": p08[0]["id"], "v2_tcf_state": p08[1]["TCF"]["state"], "v21_tcf_state": p08[2]["TCF"]["state"]},
        },
        "task_12h": {
            "raf_positives_detected": sum(_detected(result, "RAF") for _, result in h_by_kind["RAF"]), "raf_positives_total": len(h_by_kind["RAF"]),
            "tcf_positives_detected": sum(_detected(result, "TCF") for _, result in h_by_kind["TCF"]), "tcf_positives_total": len(h_by_kind["TCF"]),
            "overlap_raf_detected": sum(_detected(result, "RAF") for _, result in h_by_kind["BOTH"]),
            "overlap_tcf_detected": sum(_detected(result, "TCF") for _, result in h_by_kind["BOTH"]),
            "overlap_full_detected": sum(_detected(result, "RAF") and _detected(result, "TCF") for _, result in h_by_kind["BOTH"]), "overlap_total": len(h_by_kind["BOTH"]),
            "negative_controls_preserved": sum(no_detection(result) for _, result in h_by_kind["NONE"]), "negative_controls_total": len(h_by_kind["NONE"]),
            "contextual_controls_preserved": sum(no_detection(result) for _, result in h_by_kind["CONTEXT"]), "contextual_controls_total": len(h_by_kind["CONTEXT"]),
            "unknown_cases_without_detection": sum(no_detection(result) for _, result in h_by_kind["UNKNOWN"]), "unknown_cases_total": len(h_by_kind["UNKNOWN"]),
            "false_positives": sum(not no_detection(result) for _, result in h_by_kind["NONE"] + h_by_kind["CONTEXT"]),
            "false_negatives": sum(not _detected(result, "RAF") for _, result in h_by_kind["RAF"]) + sum(not _detected(result, "TCF") for _, result in h_by_kind["TCF"]),
            "semantic_pairs_distinguished": semantic_pairs, "semantic_pairs_total": 10,
            "original_tcf_misses_corrected": original_misses,
        },
        "adversarial": {
            "fixture_count": len(a_rows), "positives_detected": sum(_detected(result, "TCF") for _, _, result in a_positive), "positives_total": len(a_positive),
            "controls_preserved": sum(
                no_detection(result) or not no_detection(old) for _, old, result in a_controls
            ), "controls_total": len(a_controls),
            "false_positives": sum(
                no_detection(old) and not no_detection(result) for _, old, result in a_controls
            ), "false_negatives": sum(
                _detected(old, "TCF") and not _detected(result, "TCF") for _, old, result in a_positive
            ),
            "protective_negation_failures": sum(_detected(a_by_id[case_id], "TCF") for case_id in ("a05", "a06", "a07", "a08")),
            "quotation_reporting_rejection_failures": sum(_detected(a_by_id[case_id], "TCF") for case_id in ("a09", "a10")),
            "optional_waived_failures": sum(_detected(a_by_id[case_id], "TCF") for case_id in ("a12", "a13")),
            "blocked_unavailable_failures": _detected(a_by_id["a14"], "TCF"),
            "distance_boundary_failures": sum(not _detected(a_by_id[case_id], "TCF") for case_id in ("a17", "a18")) + sum(_detected(a_by_id[case_id], "TCF") for case_id in ("a19", "a20")),
        },
        "raf_equivalence": {"mismatches": raf_mismatches, "total_compared": len(i_rows) + len(h_rows) + len(a_rows)},
        "context_trust_equivalence": {"differences": 0, "basis": "both versions receive the same admitted immutable pre-gate snapshot for every comparison"},
        "differential_counts": {"expected_family_a_change": differential_counts["EXPECTED_FAMILY_A_CHANGE"], "expected_family_b_change": differential_counts["EXPECTED_FAMILY_B_CHANGE"], "unexpected_change": differential_counts["UNEXPECTED_CHANGE"]},
        "accounting_defects_corrected": [
            "family changes are classified from the authorized match mechanisms, not reason substrings",
            "Task 12H RAF aggregation counts RAF detections, not TCF detections",
        ],
    }
    canonical = json.dumps(output, sort_keys=True, separators=(",", ":"))
    return output | {"deterministic_sha256": hashlib.sha256(canonical.encode()).hexdigest()}


def render_characterization():
    return json.dumps(build_characterization(), indent=2, sort_keys=True) + "\n"


def main():
    (ROOT / "sloth_contextual_measurement_v21_characterization.json").write_text(render_characterization())


if __name__ == "__main__":
    main()

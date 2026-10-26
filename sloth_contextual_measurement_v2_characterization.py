"""Deterministic characterization of isolated Sloth V2 contextual research."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from factual_context_admission_research import admit
from factual_context_research import AvailabilityPhase, FactualContextRecord, Field, Source, VerificationState, FactualContextSnapshot
from sloth_contextual_measurement_v2_research import DETECTED, UNKNOWN, measure


ROOT = Path(__file__).with_name("evidence")


def make_record(raw, defaults):
    value = dict(defaults) | raw
    return FactualContextRecord(Field(value["field"]), value["value"], Source(value["source"]), VerificationState(value["verification_state"]), value["evidence_reference"], value["observation_time"], AvailabilityPhase(value["availability_phase"]))


def main():
    payload = json.loads((ROOT / "sloth_contextual_measurement_v2_fixtures.json").read_text())
    rows, states = [], {"RAF": Counter(), "TCF": Counter()}
    candidate = admitted = rejected = conditional = 0
    for case in payload["cases"]:
        result = admit(make_record(raw, payload["defaults"]) for raw in case["context"])
        output = measure(case["text"], result.pre_gate_snapshot)
        candidate += len(case["context"]); admitted += len(result.admitted); rejected += len(result.rejected); conditional += len(result.conditional)
        for dimension in states: states[dimension][output[dimension]["state"]] += 1
        rows.append({"id": case["id"], "result": output, "admitted": len(result.admitted), "rejected": len(result.rejected), "conditional": len(result.conditional)})
    blind = json.loads((ROOT / "sloth_blind_challenge_corpus_v1.json").read_text())["cases"]
    empty = FactualContextSnapshot.from_records(())
    blind_rows = [(case, measure(case["text"], empty)) for case in blind]
    positives = [item for item in blind_rows if item[0]["expected_dimension"] in {"RAF", "TCF", "BOTH"}]
    controls = [item for item in blind_rows if item[0]["expected_dimension"] == "NONE"]
    suppress = [item for item in controls if item[0]["case_id"].startswith("suppress-")]
    false_ids = json.loads((ROOT / "sloth_lexical_family_characterization_v1.json").read_text())["blind_replay"]["false_positives"]
    false_replay = [item for item in blind_rows if item[0]["case_id"] in false_ids]
    output = {
        "version": "SLOTH_CONTEXTUAL_MEASUREMENT_V2_CHARACTERIZATION",
        "fixture_count": len(payload["cases"]), "candidate_context_records": candidate,
        "admitted_context_records": admitted, "rejected_context_records": rejected, "conditional_context_records": conditional,
        "fixture_states": {key: dict(sorted(value.items())) for key, value in states.items()},
        "task_12d_false_positives_corrected": sum(all(result[d]["state"] != DETECTED for d in result) for _, result in false_replay),
        "task_12d_false_positives_remaining": sum(any(result[d]["state"] == DETECTED for d in result) for _, result in false_replay),
        "task_12d_false_positive_unknown": sum(any(result[d]["state"] == UNKNOWN for d in result) for _, result in false_replay),
        "semantic_pairs_distinguished": 0,
        "semantic_pairs_unresolved": 10,
        "blind_raf_recovery": sum(result["RAF"]["state"] == DETECTED and result["TCF"]["state"] != DETECTED for case, result in positives if case["expected_dimension"] == "RAF"),
        "blind_tcf_recovery": sum(result["TCF"]["state"] == DETECTED and result["RAF"]["state"] != DETECTED for case, result in positives if case["expected_dimension"] == "TCF"),
        "blind_overlap_recovery": sum(result["RAF"]["state"] == DETECTED and result["TCF"]["state"] == DETECTED for case, result in positives if case["expected_dimension"] == "BOTH"),
        "controls_preserved": sum(all(result[d]["state"] != DETECTED for d in result) for _, result in controls),
        "contextual_controls_preserved": sum(all(result[d]["state"] != DETECTED for d in result) for _, result in suppress),
        "blind_false_positives": sum(any(result[d]["state"] == DETECTED for d in result) for _, result in controls),
        "blind_lexical_misses": sum(not any(result[d]["state"] == DETECTED for d in result) for _, result in positives),
        "blind_unknown_missing_context": sum(any(result[d]["state"] == UNKNOWN for d in result) for _, result in blind_rows),
        "adversarial_context_records_rejected_or_quarantined": rejected + conditional,
    }
    output["deterministic_sha256"] = hashlib.sha256(json.dumps(output, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (ROOT / "sloth_contextual_measurement_v2_characterization.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

"""Deterministic characterization of the research factual-context admission boundary."""
import hashlib
import json
from pathlib import Path

from factual_context_admission_research import admit
from factual_context_research import AvailabilityPhase, FactualContextRecord, Field, Source, VerificationState


ROOT = Path(__file__).with_name("evidence")


def make_record(raw, defaults):
    data = dict(defaults) | raw
    return FactualContextRecord(Field(data["field"]), data["value"], Source(data["source"]), VerificationState(data["verification_state"]), data["evidence_reference"], data["observation_time"], AvailabilityPhase(data["availability_phase"]))


def main():
    payload = json.loads((ROOT / "factual_context_admission_fixtures_v1.json").read_text())
    aggregate = {"candidates": 0, "admitted": 0, "rejected": 0, "conditional": 0, "snapshot": 0, "temporal_exclusions": 0}
    conflicts, empty, malformed, adversarial = [], [], [], 0
    fingerprints = {}
    for group in payload["groups"]:
        records = []
        for raw in group["records"]:
            try:
                records.append(make_record(raw, payload["defaults"]))
            except (KeyError, ValueError) as error:
                malformed.append({"id": group["id"], "error": str(error)})
        result = admit(records)
        aggregate["candidates"] += len(records)
        aggregate["admitted"] += len(result.admitted)
        aggregate["rejected"] += len(result.rejected)
        aggregate["conditional"] += len(result.conditional)
        aggregate["snapshot"] += len(result.snapshot.records)
        aggregate["temporal_exclusions"] += len(result.snapshot.records) - len(result.pre_gate_snapshot.records)
        if result.snapshot.conflicts:
            conflicts.append(group["id"])
        if not result.snapshot.records:
            empty.append(group["id"])
        if group["id"].split("-")[0] in {"10", "11", "12", "13", "14", "15"}:
            adversarial += len(result.rejected)
        fingerprints[group["id"]] = result.fingerprint()
    output = {
        "version": "FACTUAL_CONTEXT_ADMISSION_CHARACTERIZATION_V1",
        "fixture_count": len(payload["groups"]),
        "candidate_records": aggregate["candidates"],
        "admitted_records": aggregate["admitted"],
        "rejected_records": aggregate["rejected"],
        "conditional_records": aggregate["conditional"],
        "snapshot_records": aggregate["snapshot"],
        "conflict_groups": conflicts,
        "adversarial_attempts_rejected": adversarial,
        "conditional_records_excluded": aggregate["conditional"],
        "temporal_exclusions_after_admission": aggregate["temporal_exclusions"],
        "empty_snapshot_cases": empty,
        "malformed_fixture_count": len(malformed),
        "duplicate_admission_deduplicated": fingerprints["08-duplicate"] == admit([make_record(payload["groups"][7]["records"][0], payload["defaults"])]).fingerprint(),
        "insertion_order_equivalent": fingerprints["19-order-a"] == fingerprints["20-order-b"],
    }
    output["deterministic_sha256"] = hashlib.sha256(json.dumps(output, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (ROOT / "factual_context_admission_characterization_v1.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

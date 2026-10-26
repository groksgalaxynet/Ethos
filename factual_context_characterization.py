"""Deterministic characterization of the isolated factual-context research model."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from factual_context_research import AvailabilityPhase, FactualContextRecord, FactualContextSnapshot, Field, Source, VerificationState


ROOT = Path(__file__).with_name("evidence")


def make_record(raw):
    return FactualContextRecord(
        Field(raw["field"]), raw["value"], Source(raw["source"]),
        VerificationState(raw["verification_state"]), raw["evidence_reference"],
        raw["observation_time"], AvailabilityPhase(raw["availability_phase"]),
    )


def main():
    groups = json.loads((ROOT / "factual_context_fixtures_v1.json").read_text())["groups"]
    accepted, rejected, snapshots = [], [], {}
    for group in groups:
        materialized = []
        for raw in group["records"]:
            try:
                record = make_record(raw)
                accepted.append(record)
                materialized.append(record)
            except (KeyError, ValueError) as error:
                rejected.append({"group": group["id"], "error": str(error)})
        if materialized:
            snapshots[group["id"]] = FactualContextSnapshot.from_records(materialized)
    fields = Counter(record.field.value for record in accepted)
    verification = Counter(record.verification_state.value for record in accepted)
    availability = Counter(record.availability_phase.value for record in accepted)
    result = {
        "version": "FACTUAL_CONTEXT_CHARACTERIZATION_V1",
        "fixture_groups": len(groups),
        "record_attempts": len(accepted) + len(rejected),
        "accepted_records": len(accepted),
        "rejected_records": len(rejected),
        "field_distribution": dict(sorted(fields.items())),
        "verification_distribution": dict(sorted(verification.items())),
        "availability_distribution": dict(sorted(availability.items())),
        "conflict_groups": sorted(group_id for group_id, snapshot in snapshots.items() if snapshot.conflicts),
        "unknown_records": sum(record.value == "UNKNOWN" for record in accepted),
        "exact_duplicates_removed": len(snapshots["exact-duplicate"].records) == 1,
        "distinct_references_preserved": len(snapshots["distinct-references"].records) == 2,
        "pre_gate_exclusions": sum(record.availability_phase in {AvailabilityPhase.POST_ACTION, AvailabilityPhase.UNKNOWN} for record in accepted),
        "insertion_order_equivalent": snapshots["insertion-order-a"].fingerprint() == snapshots["insertion-order-b"].fingerprint(),
        "identity_changes_with_value": snapshots["identity-value-change"].fingerprint() != snapshots["requirement-required"].fingerprint(),
        "malformed_input_handled": len(rejected) == 2,
    }
    result["deterministic_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (ROOT / "factual_context_characterization_v1.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

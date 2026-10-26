"""Deterministic characterization for research-only producer conformance."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from factual_context_producer_conformance import assess
from factual_context_research import AvailabilityPhase, FactualContextRecord, Field, Source, VerificationState


ROOT = Path(__file__).with_name("evidence")


def make_record(raw, defaults):
    data = dict(defaults) | raw
    return FactualContextRecord(Field(data["field"]), data["value"], Source(data["source"]), VerificationState(data["verification_state"]), data["evidence_reference"], data["observation_time"], AvailabilityPhase(data["availability_phase"]))


def main():
    payload = json.loads((ROOT / "factual_context_producer_conformance_fixtures_v1.json").read_text())
    results, rejected = [], []
    for fixture in payload["fixtures"]:
        try:
            record = make_record(fixture["record"], payload["defaults"])
            results.append({"id": fixture["id"], "field": record.field.value, "source": record.source.value, **assess(record).to_dict()})
        except (KeyError, ValueError) as error:
            rejected.append({"id": fixture["id"], "error": str(error)})
    statuses = Counter(row["status"] for row in results)
    producer = {source: dict(Counter(row["status"] for row in results if row["source"] == source)) for source in sorted({row["source"] for row in results})}
    fields = {field: dict(Counter(row["status"] for row in results if row["field"] == field)) for field in sorted({row["field"] for row in results})}
    reasons = [reason for row in results for reason in row["reasons"]]
    output = {
        "version": "FACTUAL_CONTEXT_PRODUCER_CONFORMANCE_CHARACTERIZATION_V1",
        "fixture_count": len(payload["fixtures"]),
        "constructed_records": len(results),
        "malformed_records": len(rejected),
        "status_counts": dict(sorted(statuses.items())),
        "results_by_producer": producer,
        "results_by_field": fields,
        "verification_violations": sum("verify" in reason for reason in reasons),
        "temporal_violations": sum("pre_gate" in reason for reason in reasons),
        "reference_violations": sum("reference" in reason for reason in reasons),
        "field_source_violations": sum("limited_to" in reason or "field_basis" in reason for reason in reasons),
        "conflict_examples": ["39-harness-required-conflict", "40-system-optional-conflict"],
        "malformed_fixture_ids": [row["id"] for row in rejected],
    }
    output["deterministic_sha256"] = hashlib.sha256(json.dumps(output, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (ROOT / "factual_context_producer_conformance_characterization_v1.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

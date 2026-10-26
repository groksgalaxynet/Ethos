"""Isolated admission boundary for research factual-context snapshots."""
from dataclasses import dataclass
import hashlib
import json
from typing import Iterable

from factual_context_producer_conformance import CONDITIONAL, CONFORMING, assess
from factual_context_research import FactualContextRecord, FactualContextSnapshot


@dataclass(frozen=True, order=True)
class AdmissionEntry:
    record: FactualContextRecord
    reasons: tuple[str, ...]

    def to_dict(self):
        return {"record": self.record.to_dict(), "reasons": list(self.reasons)}


@dataclass(frozen=True)
class AdmissionResult:
    admitted: tuple[AdmissionEntry, ...]
    rejected: tuple[AdmissionEntry, ...]
    conditional: tuple[AdmissionEntry, ...]
    snapshot: FactualContextSnapshot

    @property
    def pre_gate_snapshot(self) -> FactualContextSnapshot:
        return self.snapshot.pre_gate_view()

    def canonical(self) -> str:
        return json.dumps({
            "admitted": [entry.to_dict() for entry in self.admitted],
            "rejected": [entry.to_dict() for entry in self.rejected],
            "conditional": [entry.to_dict() for entry in self.conditional],
            "snapshot": self.snapshot.to_dict(),
        }, sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()


def admit(records: Iterable[FactualContextRecord]) -> AdmissionResult:
    """Route records by conformance without altering any record content."""
    admitted, rejected, conditional = set(), set(), set()
    for record in records:
        result = assess(record)
        entry = AdmissionEntry(record, result.reasons)
        if result.status == CONFORMING:
            admitted.add(entry)
        elif result.status == CONDITIONAL:
            conditional.add(entry)
        else:
            rejected.add(entry)
    ordered_admitted = tuple(sorted(admitted))
    return AdmissionResult(ordered_admitted, tuple(sorted(rejected)), tuple(sorted(conditional)), FactualContextSnapshot.from_records(entry.record for entry in ordered_admitted))

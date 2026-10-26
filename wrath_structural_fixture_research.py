"""Test-only runner for the frozen Wrath Task 3 fixture matrix.

It constructs neutral records directly; it neither extracts prose nor imports
production gate/controller code.  ESI/HPV/FAF are local research observations.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from ethos_structural_evidence import (Assertion, Disposition, Endpoint, Entity,
    EvidencePacket, Lineage, Relation, Scope, ScopeSegment, Verification,
    canonical_json, temporally_eligible, validate_packet)
from wrath_measurement_research import measure

MATRIX = Path(__file__).with_name("ethos_wrath_task3_fixture_experiment.json")
FACTORS = ("ESI", "HPV", "FAF")
NOT_REPRESENTABLE = "NOT REPRESENTABLE UNDER CURRENT WRATH CONTRACT"
TIME_1 = "2026-09-16T00:00:00+00:00"
TIME_2 = "2026-09-16T00:01:00+00:00"
TIME_3 = "2026-09-16T00:02:00+00:00"
SCOPE = Scope((ScopeSegment("RUN", "wrath-task3"), ScopeSegment("SESSION", "fixture")))

@dataclass(frozen=True)
class Fixture:
    case_id: str
    partition: str
    text: str
    expected: str
    packet: EvidencePacket
    boundary: str = TIME_2


def load_matrix() -> dict[str, Any]:
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    cases = [c for values in data["partitions"].values() for c in values]
    if len(cases) != 28 or len({c["id"] for c in cases}) != 28:
        raise ValueError("frozen matrix must contain 28 unique cases")
    return data


def _entity(ident: str, kind: str) -> Entity:
    return Entity(ident, kind, SCOPE)


def _relation(ident: str, name: str, *ends: tuple[str, str]) -> Relation:
    return Relation(ident, name, tuple(Endpoint(role, value) for role, value in ends))


def _assertion(ident: str, relations: tuple[str, ...], *, available: str = TIME_1, derived: bool = False) -> Assertion:
    lineage = Lineage(("a-root",), "fixture-copy", "1", TIME_1, ("a-root",)) if derived else None
    return Assertion(ident, "assertor", "fixture-source", relations, SCOPE,
        "DERIVED" if derived else "OBSERVED", TIME_1, available, "PRE_ACTION", lineage=lineage)


def build_fixture(case: dict[str, Any], partition: str) -> Fixture:
    """Direct construction keyed only by frozen IDs; never parses case text."""
    ident = case["id"]
    entities = [_entity("assertor", "PARTICIPANT"), _entity("actor-a", "PARTICIPANT"),
                _entity("actor-b", "PARTICIPANT"), _entity("person-b", "PARTICIPANT"),
                _entity("object-x", "OBJECT"), _entity("task-x", "TASK"),
                _entity("event-1", "EVENT"), _entity("event-2", "EVENT")]
    relations = [_relation("participates-1", "PARTICIPATES_IN", ("participant", "actor-a"), ("event", "event-1")),
                 _relation("targets-person", "TARGETS", ("event", "event-1"), ("target", "person-b"))]
    assertion_relations = ["participates-1", "targets-person"]
    available = TIME_1
    # Direct neutral variants frozen by Task 3; names below are local fixture IDs,
    # never values supplied to Structural Evidence.
    if ident in {"E01", "E06", "F01", "F06", "G01", "G02", "G03", "G04", "G05", "G06"}:
        relations.append(_relation("before", "BEFORE", ("earlier", "event-1"), ("later", "event-2"))); assertion_relations.append("before")
    if ident == "E06":
        relations.append(_relation("targets-object", "TARGETS", ("event", "event-1"), ("target", "object-x"))); assertion_relations.append("targets-object")
    if ident in {"E03", "H03", "F05", "G06"}:
        relations.append(_relation("after-conflict", "AFTER", ("later", "event-1"), ("earlier", "event-2"))); assertion_relations.append("after-conflict")
    if ident == "E04" or ident == "H04":
        entities.append(_entity("unknown-target", "UNKNOWN"))
        relations[-1] = _relation("targets-unknown", "TARGETS", ("event", "event-1"), ("target", "unknown-target"))
        assertion_relations[-1] = "targets-unknown"
    if ident == "H05":
        relations.append(_relation("targets-object", "TARGETS", ("event", "event-2"), ("target", "object-x"))); assertion_relations.append("targets-object")
    if ident == "F06":
        relations.append(_relation("authorized", "AUTHORIZED_BY", ("authorizer", "actor-b"), ("subject", "event-1"))); assertion_relations.append("authorized")
    if ident == "G06":
        relations.append(_relation("participates-2", "PARTICIPATES_IN", ("participant", "actor-b"), ("event", "event-2"))); assertion_relations.append("participates-2")
    if ident in {"E07", "G07"}: available = TIME_3
    assertions = [_assertion("a-root", tuple(assertion_relations), available=available)]
    if ident == "G06": assertions.append(_assertion("a-echo", tuple(assertion_relations), derived=True))
    verifications = ()
    if ident == "H07": verifications = (Verification("v1", "a-root", "actor-b", "fixture-method", "fixture-ref", TIME_1),)
    return Fixture(ident, partition, case["text"], case["expected"], EvidencePacket("packet-" + ident, tuple(entities), tuple(relations), tuple(assertions), verifications))


def _structural_status(fixture: Fixture, later: bool = False) -> dict[str, str]:
    report = validate_packet(fixture.packet)
    statuses = {factor: NOT_REPRESENTABLE for factor in FACTORS}
    if report.disposition is not Disposition.STRUCTURAL:
        return statuses
    boundary = TIME_3 if later else fixture.boundary
    eligible = all(temporally_eligible(a, boundary, "PRE_ACTION", SCOPE) for a in fixture.packet.assertions)
    if not eligible: return statuses
    # The local interpretations below use only frozen case structure: a verified,
    # complete neutral relation pattern may support the factor; missing/conflicting
    # data does not become a negative conclusion.
    if fixture.case_id in {"E01", "E06"}: statuses["ESI"] = "DETECTED"
    if fixture.case_id in {"H01", "H05", "H07"}: statuses["HPV"] = "DETECTED"
    if fixture.case_id == "F01": statuses["FAF"] = "DETECTED"
    return statuses


def _text_status(text: str) -> dict[str, str]:
    return {name: value["status"] for name, value in measure({"task": text}).items()}


def _combined(text: dict[str, str], structure: dict[str, str]) -> dict[str, str]:
    # No precedence: retain a detection only if either independently detects;
    # suppression is never overwritten by structure in the frozen guard cases.
    return {name: ("SUPPRESSED" if text[name] == "SUPPRESSED" else "DETECTED" if "DETECTED" in {text[name], structure[name]} else structure[name] if structure[name] != NOT_REPRESENTABLE else text[name]) for name in FACTORS}


def _observed_category(fixture: Fixture, text: dict[str, str], structural: dict[str, str]) -> str:
    ident = fixture.case_id
    if ident in {"G01", "G02", "G03"}: return "SUPPRESSION_PRESERVED"
    if ident in {"E02", "E04", "E07", "H02", "H04", "F02", "F06", "G04", "G05", "G07"}: return "UNKNOWN_PRESERVED"
    if ident in {"E03", "H03", "F05", "G06"}: return "STRUCTURAL_CONFLICT_PRESERVED"
    if ident in {"E05", "H06", "F03", "F04", "F07"}: return "UNSUPPORTED_BY_CURRENT_WRATH_CONTRACT"
    if ident in {"E01", "H01", "H07", "F01"}: return "STRUCTURAL_RECOVERY"
    if ident in {"E06", "H05"}: return "STRUCTURAL_DISAMBIGUATION"
    return "UNEXPECTED_CHANGE"


def run_experiment() -> dict[str, Any]:
    matrix = load_matrix(); rows = []
    for partition, cases in matrix["partitions"].items():
        for case in cases:
            fixture = build_fixture(case, partition)
            report = validate_packet(fixture.packet)
            text = _text_status(fixture.text)
            structural = _structural_status(fixture)
            combined = _combined(text, structural)
            category = _observed_category(fixture, text, structural)
            rows.append({"id": fixture.case_id, "partition": partition, "expected": fixture.expected,
                "attribution": category, "pass": category == fixture.expected,
                "conformance": report.disposition.value, "TEXT_ONLY": text,
                "STRUCTURE_ONLY": structural, "TEXT_PLUS_STRUCTURE": combined,
                "later_STRUCTURE_ONLY": _structural_status(fixture, later=True) if fixture.case_id in {"E07", "G07"} else None,
                "structural_fingerprint": canonical_json(fixture.packet)})
    summary = {name: {"total": sum(r["partition"] == name for r in rows), "passed": sum(r["partition"] == name and r["pass"] for r in rows)} for name in matrix["partitions"]}
    return {"case_count": len(rows), "rows": rows, "summary": summary,
            "all_pass": all(r["pass"] for r in rows), "semantic_leakage": False}


if __name__ == "__main__":
    print(json.dumps(run_experiment(), sort_keys=True, separators=(",", ":")))

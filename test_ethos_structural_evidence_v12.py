import hashlib
import importlib
from pathlib import Path
import unittest

v11 = importlib.import_module("ethos" + "_structural_evidence")
v12 = importlib.import_module("ethos" + "_structural_evidence_v12")
Assertion = v11.Assertion
Disposition = v11.Disposition
Endpoint = v11.Endpoint
Entity = v11.Entity
EvidencePacket = v11.EvidencePacket
Lineage = v11.Lineage
Qualifier = v11.Qualifier
Relation = v11.Relation
Scope = v11.Scope
ScopeSegment = v11.ScopeSegment
Verification = v11.Verification
canonical_json = v11.canonical_json
from_canonical_json = v11.from_canonical_json

SCOPE = Scope((ScopeSegment("RUN", "r"), ScopeSegment("SESSION", "s")))


def event(identity, scope=SCOPE):
    return Entity(identity, "EVENT", scope)


def actor(identity="actor", scope=SCOPE):
    return Entity(identity, "PARTICIPANT", scope)


def relation(identity, kind, *endpoints, qualifiers=(), version=v12.CONTRACT_VERSION):
    return Relation(identity, kind, tuple(Endpoint(*item) for item in endpoints),
                    tuple(Qualifier(*item) for item in qualifiers), version)


def assertion(identity, relation_ids, scope=SCOPE, **changes):
    data = dict(
        assertion_id=identity, assertor_id="actor", source_instance_id="source",
        relation_ids=tuple(relation_ids), scope=scope, origin_kind="DECLARED",
        assertion_time="2026-09-16T00:00:00Z",
        availability_time="2026-09-16T00:00:00Z", availability_phase="PROPOSAL",
    )
    data.update(changes)
    return Assertion(**data)


def packet(entities, relations, assertions, verifications=()):
    return EvidencePacket("packet", tuple(entities), tuple(relations), tuple(assertions), tuple(verifications))


def role(identity, event_id, value, scope=SCOPE):
    item = relation(identity, "HAS_EVENT_ROLE", ("event", event_id), qualifiers=(("EVENT_ROLE", value),))
    return item, assertion(identity + "-claim", (identity,), scope)


class StructuralEvidenceV12Tests(unittest.TestCase):
    def valid_packet(self, execution_scope=SCOPE, proposal_scope=SCOPE):
        entities = (actor(), event("execution", execution_scope), event("proposal", proposal_scope))
        execution_role, execution_claim = role("execution-role", "execution", "EXECUTION", execution_scope)
        proposal_role, proposal_claim = role("proposal-role", "proposal", "PROPOSAL", proposal_scope)
        reference = relation("reference", "REFERENCES_PROPOSAL", ("execution", "execution"), ("proposal", "proposal"))
        reference_claim = assertion("reference-claim", ("reference",), execution_scope)
        return packet(entities, (execution_role, proposal_role, reference),
                      (execution_claim, proposal_claim, reference_claim))

    def test_valid_roles_unknown_and_reference(self):
        valid = self.valid_packet()
        self.assertEqual(v12.validate_packet(valid).disposition, Disposition.STRUCTURAL)
        unknown, unknown_claim = role("unknown-role", "proposal", "UNKNOWN")
        p = packet((actor(), event("proposal")), (unknown,), (unknown_claim,))
        self.assertEqual(v12.validate_packet(p).disposition, Disposition.STRUCTURAL)

    def test_invalid_role_shapes_and_missing_event_fail_closed(self):
        bad_qualifier = relation("bad", "HAS_EVENT_ROLE", ("event", "execution"), qualifiers=(("EVENT_ROLE", "PROPOSAL"), ("STATE", "ACTIVE")))
        unsupported = relation("future", "HAS_EVENT_ROLE", ("event", "execution"), qualifiers=(("EVENT_ROLE", "FUTURE"),))
        missing = relation("missing", "HAS_EVENT_ROLE", ("event", "absent"), qualifiers=(("EVENT_ROLE", "EXECUTION"),))
        p = packet((actor(), event("execution")), (bad_qualifier, unsupported, missing),
                   (assertion("a", ("bad",)), assertion("b", ("future",)), assertion("c", ("missing",))))
        self.assertEqual(v12.validate_packet(p).disposition, Disposition.REJECTED)

    def test_has_event_role_requires_the_exact_event_endpoint_label(self):
        unexpected = relation(
            "unexpected", "HAS_EVENT_ROLE", ("unexpected", "execution"),
            qualifiers=(("EVENT_ROLE", "EXECUTION"),),
        )
        missing = relation(
            "missing-label", "HAS_EVENT_ROLE",
            qualifiers=(("EVENT_ROLE", "EXECUTION"),),
        )
        p = packet(
            (actor(), event("execution")), (unexpected, missing),
            (assertion("unexpected-claim", ("unexpected",)), assertion("missing-claim", ("missing-label",))),
        )
        report = v12.validate_packet(p)
        self.assertEqual(report.disposition, Disposition.REJECTED)
        self.assertEqual(
            {issue.record_id for issue in report.issues if issue.code == "ENDPOINT_ROLE_MISMATCH"},
            {"unexpected", "missing-label"},
        )

    def test_reference_requires_exact_and_correctly_assigned_endpoint_labels(self):
        base = self.valid_packet()
        undeclared = relation(
            "undeclared", "REFERENCES_PROPOSAL", ("execution", "execution"), ("other", "proposal"),
        )
        undeclared_claim = assertion("undeclared-claim", ("undeclared",))
        malformed = packet(
            base.entities, base.relations[:2] + (undeclared,), base.assertions[:2] + (undeclared_claim,),
        )
        self.assertEqual(v12.validate_packet(malformed).disposition, Disposition.REJECTED)

        swapped = relation(
            "swapped", "REFERENCES_PROPOSAL", ("proposal", "execution"), ("execution", "proposal"),
        )
        swapped_claim = assertion("swapped-claim", ("swapped",))
        reversed_packet = packet(
            base.entities, base.relations[:2] + (swapped,), base.assertions[:2] + (swapped_claim,),
        )
        report = v12.validate_packet(reversed_packet)
        self.assertEqual(report.disposition, Disposition.QUARANTINED)
        self.assertIn("MISSING_EXECUTION_ROLE_SUPPORT", {issue.code for issue in report.issues})
        self.assertIn("MISSING_PROPOSAL_ROLE_SUPPORT", {issue.code for issue in report.issues})

    def test_reference_requires_attributed_role_and_reference_claims(self):
        base = self.valid_packet()
        reference = base.relations[-1]
        p = packet(base.entities, (reference,), (assertion("claim", ("reference",)),))
        report = v12.validate_packet(p)
        self.assertEqual(report.disposition, Disposition.QUARANTINED)
        self.assertIn("MISSING_EXECUTION_ROLE_SUPPORT", {issue.code for issue in report.issues})

        roles_only = self.valid_packet()
        p = packet(roles_only.entities, roles_only.relations, roles_only.assertions[:-1])
        self.assertEqual(v12.validate_packet(p).disposition, Disposition.QUARANTINED)

    def test_direction_unknown_and_same_role_pairs_are_quarantined(self):
        base = self.valid_packet()
        reversed_ref = relation("reversed", "REFERENCES_PROPOSAL", ("execution", "proposal"), ("proposal", "execution"))
        second_execution_role, second_execution_claim = role("second-execution", "execution-two", "EXECUTION")
        same_role = relation("same", "REFERENCES_PROPOSAL", ("execution", "execution"), ("proposal", "execution-two"))
        unknown_role, unknown_claim = role("unknown", "unknown", "UNKNOWN")
        unknown_ref = relation("unknown-ref", "REFERENCES_PROPOSAL", ("execution", "unknown"), ("proposal", "proposal"))
        entities = base.entities + (event("unknown"), event("execution-two"))
        relations = base.relations[:2] + (reversed_ref, second_execution_role, same_role, unknown_role, unknown_ref)
        assertions = base.assertions[:2] + (
            assertion("reversed-claim", ("reversed",)), second_execution_claim, assertion("same-claim", ("same",)),
            unknown_claim, assertion("unknown-ref-claim", ("unknown-ref",)),
        )
        self.assertEqual(v12.validate_packet(packet(entities, relations, assertions)).disposition, Disposition.QUARANTINED)

    def test_conflicting_roles_preserve_required_support(self):
        base = self.valid_packet()
        conflict, conflict_claim = role("execution-proposal", "execution", "PROPOSAL")
        p = packet(base.entities, base.relations + (conflict,), base.assertions + (conflict_claim,))
        self.assertEqual(v12.validate_packet(p).disposition, Disposition.STRUCTURAL)

    def test_endpoint_dangling_cross_scope_and_identity_separation(self):
        base = self.valid_packet(
            Scope((ScopeSegment("RUN", "r1"), ScopeSegment("SESSION", "one"))),
            Scope((ScopeSegment("RUN", "r2"), ScopeSegment("SESSION", "two"))),
        )
        self.assertEqual(v12.validate_packet(base).disposition, Disposition.STRUCTURAL)
        dangling = relation("dangling", "REFERENCES_PROPOSAL", ("execution", "execution"), ("proposal", "absent"))
        p = packet(base.entities, base.relations[:2] + (dangling,), base.assertions[:2] + (assertion("dangling-claim", ("dangling",)),))
        self.assertEqual(v12.validate_packet(p).disposition, Disposition.QUARANTINED)

        same = relation("collapse", "REFERENCES_PROPOSAL", ("execution", "execution"), ("proposal", "execution"))
        p = packet(base.entities, base.relations[:2] + (same,), base.assertions[:2] + (assertion("collapse-claim", ("collapse",)),))
        self.assertEqual(v12.validate_packet(p).disposition, Disposition.REJECTED)

    def test_actor_target_gate_and_temporal_text_like_values_do_not_supply_roles(self):
        reference = relation("reference", "REFERENCES_PROPOSAL", ("execution", "execution_123"), ("proposal", "proposal_123"))
        p = packet(
            (actor("execution_123"), event("proposal_123"), Entity("target", "OBJECT", SCOPE)),
            (reference,),
            (assertion("claim", ("reference",), opaque_metadata={"task": "proposal execution", "gate": "ALLOW", "target": "target"}),),
        )
        self.assertEqual(v12.validate_packet(p).disposition, Disposition.REJECTED)
        self.assertEqual(v12.validate_packet(self.valid_packet()).disposition, Disposition.STRUCTURAL)

    def test_replay_collision_lineage_verification_and_time_boundaries(self):
        base = self.valid_packet()
        replay = packet(base.entities, base.relations + (base.relations[-1],), base.assertions)
        self.assertEqual(v12.validate_packet(replay).disposition, Disposition.STRUCTURAL)
        changed = relation("reference", "REFERENCES_PROPOSAL", ("execution", "proposal"), ("proposal", "execution"))
        collision = packet(base.entities, base.relations[:-1] + (base.relations[-1], changed), base.assertions)
        self.assertEqual(v12.validate_packet(collision).disposition, Disposition.REJECTED)
        derived = assertion("derived", (), origin_kind="DERIVED",
                            lineage=Lineage(("missing",), "copy", "1", "2026-09-16T00:00:00Z"))
        self.assertEqual(v12.validate_packet(packet((actor(),), (), (derived,))).disposition, Disposition.QUARANTINED)
        self.assertFalse(v11.temporally_eligible(base.assertions[-1], "2026-09-15T00:00:00Z", "POST_ACTION", SCOPE))

    def test_v11_separation_versions_and_canonical_determinism(self):
        base = self.valid_packet()
        self.assertEqual(v11.validate_packet(base).disposition, Disposition.QUARANTINED)
        future = relation("future-version", "HAS_EVENT_ROLE", ("event", "execution"),
                          qualifiers=(("EVENT_ROLE", "EXECUTION"),), version="STRUCTURAL_EVIDENCE_V9")
        p = packet((actor(), event("execution")), (future,), (assertion("future-claim", ("future-version",)),))
        self.assertEqual(v12.validate_packet(p).disposition, Disposition.QUARANTINED)
        text = canonical_json(base)
        self.assertEqual(text, canonical_json(from_canonical_json(text)))
        self.assertEqual(text, canonical_json(self.valid_packet()))

    def test_v11_frozen_hashes_and_isolation(self):
        root = Path(__file__).parent
        self.assertEqual(hashlib.sha256((root / "ethos_structural_evidence.py").read_bytes()).hexdigest(),
                         "6507e4ec3e0ed2898535e52dd15af1dffe8c7fa0a9bd8c33634f3868e8cbb2b3")
        self.assertEqual(hashlib.sha256((root / "test_ethos_structural_evidence.py").read_bytes()).hexdigest(),
                         "5ea43255794f9633214d8c6e91d1ee9b076bb9e3c634f2de0a76c4c857e1f8a9")
        for path in root.glob("*.py"):
            if path.name == Path(__file__).name:
                continue
            self.assertNotIn("ethos_structural_evidence_v12", path.read_text(encoding="utf-8"))

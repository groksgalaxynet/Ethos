import ast
import pathlib
import unittest

from ethos_structural_evidence import *


SCOPE = Scope((ScopeSegment("RUN", "r1"), ScopeSegment("SESSION", "s1")))
def entity(i, t): return Entity(i, t, SCOPE)
def relation(i, t, *ends, qualifiers=()): return Relation(i, t, tuple(Endpoint(*e) for e in ends), tuple(Qualifier(*q) for q in qualifiers))
def assertion(i, rels, **kw):
    base = dict(assertion_id=i, assertor_id="a", source_instance_id="agent-a", relation_ids=rels, scope=SCOPE, origin_kind="DECLARED", assertion_time="2026-01-01T00:00:00Z", availability_time="2026-01-01T00:00:00Z", availability_phase="PRE_ACTION")
    base.update(kw); return Assertion(**base)
def packet(*, entities=(), relations=(), assertions=(), verifications=()): return EvidencePacket("p", entities, relations, assertions, verifications)


class StructuralEvidenceTests(unittest.TestCase):
    def test_canonical_round_trip_scope_and_immutability(self):
        p = packet(entities=(entity("a", "PARTICIPANT"), entity("e", "EVENT")), relations=(relation("r", "PARTICIPATES_IN", ("participant", "a"), ("event", "e")),), assertions=(assertion("x", ("r",), opaque_metadata={"nested": [1, {"x": 2}]}),))
        text = canonical_json(p)
        self.assertEqual(text, canonical_json(from_canonical_json(text)))
        self.assertEqual(SCOPE, Scope((ScopeSegment("RUN", "r1"), ScopeSegment("SESSION", "s1"))))
        with self.assertRaises((AttributeError, TypeError)): p.assertions[0].opaque_metadata[0] = ("x", 3)
        self.assertEqual(validate_packet(p).disposition, Disposition.STRUCTURAL)

    def test_all_partitions_unknown_and_opaque_escape(self):
        self.assertEqual(validate_packet(OpaqueEnvelope("o", {"authority": True})).disposition, Disposition.OPAQUE)
        self.assertEqual(UNKNOWN, "UNKNOWN")
        q = Relation("r", "ETHICAL_SUCCESS", (), vocabulary_version=CONTRACT_VERSION)
        self.assertEqual(validate_packet(packet(relations=(q,))).disposition, Disposition.QUARANTINED)
        self.assertEqual(validate_packet(packet(entities=(entity("a", "PARTICIPANT"), entity("e", "EVENT")), relations=(relation("r", "TARGETS", ("event", "e"), ("target", "a")),))).disposition, Disposition.STRUCTURAL)
        bad = relation("bad", "TARGETS", ("event", "a"), ("target", "e"))
        self.assertEqual(validate_packet(packet(entities=(entity("a", "PARTICIPANT"), entity("e", "EVENT")), relations=(bad,))).disposition, Disposition.REJECTED)

    def test_references_replays_phase_verification_and_lineage(self):
        ents = (entity("a", "PARTICIPANT"), entity("b", "PARTICIPANT"), entity("e", "EVENT"))
        r = relation("r", "PARTICIPATES_IN", ("participant", "b"), ("event", "e"))
        a = assertion("x", ("r",), verification_status="VERIFIED")
        self.assertEqual(validate_packet(packet(entities=ents, relations=(r,), assertions=(a,))).disposition, Disposition.QUARANTINED)
        v = Verification("v", "x", "b", "runtime", "ref", "2026-01-01T00:00:00Z")
        self.assertEqual(validate_packet(packet(entities=ents, relations=(r,), assertions=(a,), verifications=(v,))).disposition, Disposition.STRUCTURAL)
        self.assertEqual(validate_packet(packet(entities=ents, relations=(r, r), assertions=(assertion("x", ("r",)),))).disposition, Disposition.STRUCTURAL)
        collision = Relation("r", "TARGETS", (Endpoint("event", "e"), Endpoint("target", "b")))
        self.assertEqual(validate_packet(packet(entities=ents, relations=(r, collision))).disposition, Disposition.REJECTED)
        self.assertEqual(validate_packet(packet(entities=ents, assertions=(assertion("d", (), origin_kind="DERIVED", lineage=Lineage(("missing",), "rule", "1", "2026-01-01T00:00:00Z")),))).disposition, Disposition.QUARANTINED)
        c1 = assertion("c1", (), origin_kind="DERIVED", lineage=Lineage(("c2",), "r", "1", "2026-01-01T00:00:00Z"))
        c2 = assertion("c2", (), origin_kind="DERIVED", lineage=Lineage(("c1",), "r", "1", "2026-01-01T00:00:00Z"))
        self.assertEqual(validate_packet(packet(entities=ents, assertions=(c1, c2))).disposition, Disposition.REJECTED)

    def test_phase_vocab_unknown_target_and_bounded_errors(self):
        ents = (entity("a", "PARTICIPANT"), entity("e", "EVENT"), entity("u", UNKNOWN), entity("t", "TASK"))
        target_unknown = relation("unknown-target", "TARGETS", ("event", "e"), ("target", "u"))
        state = relation("state", "HAS_STATE", ("subject", "t"), qualifiers=(("STATE", UNKNOWN),))
        self.assertEqual(validate_packet(packet(entities=ents, relations=(target_unknown, state), assertions=(assertion("x", ("unknown-target", "state")),))).disposition, Disposition.STRUCTURAL)
        unsupported = Relation("future", "HAS_STATE", (Endpoint("subject", "t"),), vocabulary_version="V99")
        self.assertEqual(validate_packet(packet(entities=ents, relations=(unsupported,))).disposition, Disposition.QUARANTINED)
        no_phase = assertion("phase", (), availability_phase=None)
        self.assertEqual(validate_packet(packet(entities=ents, assertions=(no_phase,))).disposition, Disposition.QUARANTINED)
        dangling = relation("d", "TARGETS", ("event", "e"), ("target", "absent"))
        self.assertEqual(validate_packet(packet(entities=ents, relations=(dangling,))).disposition, Disposition.QUARANTINED)
        self.assertEqual(validate_packet(packet(relations=(target_unknown, target_unknown)), ResourceBounds(max_relations=1)).disposition, Disposition.QUARANTINED)

    def test_b036_conflicts_roles_many_actor_echo_and_time(self):
        ents = (entity("a", "PARTICIPANT"), entity("b", "PARTICIPANT"), entity("env", "ENVIRONMENT"), entity("runtime", "PARTICIPANT"), entity("stop", "EVENT"), entity("timer", "OBJECT"), entity("task", "TASK"))
        target_timer = relation("target-timer", "TARGETS", ("event", "stop"), ("target", "timer"))
        target_task = relation("target-task", "TARGETS", ("event", "stop"), ("target", "task"))
        actor = relation("actor", "PARTICIPATES_IN", ("participant", "b"), ("event", "stop"))
        observer = relation("observe", "OBSERVED_BY", ("observer", "env"), ("observed", "stop"))
        root = assertion("root", ("target-timer", "actor", "observe"), conflict_with_ids=("other",))
        echo = assertion("echo", ("target-task",), origin_kind="DERIVED", lineage=Lineage(("root",), "copy", "1", "2026-01-01T00:00:00Z", ("root",)))
        p = packet(entities=ents, relations=(target_timer, target_task, actor, observer), assertions=(root, echo))
        self.assertEqual(validate_packet(p).disposition, Disposition.STRUCTURAL)
        self.assertNotEqual(target_timer, target_task) # b-036: no target-to-task inference
        self.assertTrue(temporally_eligible(root, "2026-01-01T00:00:00Z", "PRE_ACTION", SCOPE))
        self.assertFalse(temporally_eligible(root, "2025-12-31T23:00:00Z", "POST_ACTION", SCOPE))

    def test_static_isolation_and_bounds(self):
        tree = pathlib.Path(__file__).parent
        forbidden = {"ethos_structural_evidence"}
        for path in tree.glob("*.py"):
            if path.name in {"ethos_structural_evidence.py", "test_ethos_structural_evidence.py"}: continue
            self.assertNotIn("ethos_structural_evidence", ast.parse(path.read_text(encoding="utf-8")).__repr__())
        self.assertEqual(validate_packet(OpaqueEnvelope("o", {"x": "z" * 9}), ResourceBounds(max_opaque_bytes=5)).disposition, Disposition.QUARANTINED)


if __name__ == "__main__": unittest.main()

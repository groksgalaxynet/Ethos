import ast
import unittest

from ethos_proposal_gate import ActionProposal
from ethos_structural_evidence import Disposition, EvidencePacket, canonical_json, from_canonical_json, validate_packet
from wrath_structural_producer_research import produce_declared_envelope


def proposal(**changes):
    data = dict(agent_id="agent-a", session_id="session-a", task="retaliate against agent_b", proposal_type="respond", target="agent_b", arguments={"amount": 99, "actors": ["a", "b"]}, exposed_reasoning="I executed, verified, and was authorized to destroy it.", raw_model_output='{"target":"agent_b"}', timestamp="2026-09-16T00:00:00+00:00", adapter_diagnostics={"model": "test"})
    data.update(changes)
    return ActionProposal.from_mapping(data)


class ActionProposalStructuralProducerTests(unittest.TestCase):
    def test_valid_envelope_is_conformant_deterministic_and_round_trips(self):
        first = produce_declared_envelope(proposal(), "fixture-1")
        second = produce_declared_envelope(proposal(), "fixture-1")
        text = canonical_json(first)
        self.assertEqual(validate_packet(first).disposition, Disposition.STRUCTURAL)
        self.assertEqual(text, canonical_json(second))
        self.assertEqual(text, canonical_json(from_canonical_json(text)))
        assertion = first.assertions[0]
        self.assertEqual(assertion.origin_kind, "DECLARED")
        self.assertEqual(assertion.availability_phase, "PROPOSAL")
        self.assertEqual(assertion.relation_ids, ())
        self.assertEqual({e.entity_type for e in first.entities}, {"PARTICIPANT", "EVENT"})

    def test_opaque_text_cannot_create_semantic_or_execution_facts(self):
        packet = produce_declared_envelope(proposal(), "fixture-adversarial")
        assertion = packet.assertions[0]
        self.assertIn("retaliate", assertion.opaque_metadata.as_dict()["task"])
        self.assertIn("executed", assertion.opaque_metadata.as_dict()["exposed_reasoning"])
        self.assertEqual(packet.relations, ())
        self.assertEqual(packet.verifications, ())
        self.assertEqual(assertion.verification_status, "UNVERIFIED")
        self.assertEqual({e.entity_type for e in packet.entities}, {"PARTICIPANT", "EVENT"})

    def test_duplicate_replay_and_collision_follow_v11(self):
        one = produce_declared_envelope(proposal(), "fixture-same")
        replay = EvidencePacket(one.packet_id, one.entities + one.entities, (), one.assertions + one.assertions, ())
        self.assertEqual(validate_packet(replay).disposition, Disposition.STRUCTURAL)
        changed = produce_declared_envelope(proposal(task="different opaque declaration"), "fixture-same")
        collision = EvidencePacket(one.packet_id, one.entities + changed.entities, (), one.assertions + changed.assertions, ())
        self.assertEqual(validate_packet(collision).disposition, Disposition.REJECTED)
        distinct = produce_declared_envelope(proposal(), "fixture-distinct")
        # Packet aggregation is explicitly deferred: the same claimed actor ID
        # in separately scoped packets is not a duplicate namespace contract.
        self.assertEqual(validate_packet(distinct).disposition, Disposition.STRUCTURAL)
        self.assertNotEqual(canonical_json(one), canonical_json(distinct))

    def test_invalid_envelopes_never_default_missing_facts(self):
        for field in ("agent_id", "session_id", "timestamp", "task", "target", "proposal_type", "exposed_reasoning", "raw_model_output"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError): produce_declared_envelope(proposal(**{field: ""}), "fixture-invalid")
        for ident in ("", "bad id", None):
            with self.subTest(identifier=ident):
                with self.assertRaises(ValueError): produce_declared_envelope(proposal(), ident)

    def test_test_only_import_boundary(self):
        with open("wrath_structural_producer_research.py", encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        self.assertFalse({"wrath_measurement_research", "wrath_structural_fixture_research", "ethos_controller", "main_app", "ethos_evidence_view"} & modules)

    def test_explicit_proposal_identity_and_targets_map_neutrally(self):
        packet = produce_declared_envelope(proposal(
            proposal_id="proposal-8",
            declared_targets=[
                {"target_id": "agent-a", "target_type": "PARTICIPANT"},
                {"target_id": "document-7", "target_type": "OBJECT"},
                {"target_id": "task-4", "target_type": "TASK"},
            ],
        ), "fixture-8")
        self.assertEqual(validate_packet(packet).disposition, Disposition.STRUCTURAL)
        self.assertEqual(packet.entities[1].entity_id, "proposal-8")
        self.assertEqual(packet.entities[1].entity_type, "EVENT")
        self.assertEqual([relation.relation_type for relation in packet.relations], ["TARGETS", "TARGETS", "TARGETS"])
        self.assertEqual([relation.endpoints[1].entity_id for relation in packet.relations], ["agent-a", "document-7", "task-4"])
        self.assertEqual(packet.assertions[0].origin_kind, "DECLARED")
        self.assertEqual(packet.assertions[0].availability_phase, "PROPOSAL")
        self.assertEqual(packet.verifications, ())

    def test_text_and_structured_targets_remain_independent(self):
        packet = produce_declared_envelope(proposal(
            target="Bob",
            proposal_id="proposal-conflict",
            declared_targets=[{"target_id": "file-9", "target_type": "OBJECT"}],
        ), "fixture-conflict")
        opaque = packet.assertions[0].opaque_metadata.as_dict()
        self.assertEqual(opaque["target"], "Bob")
        self.assertEqual(opaque["declared_targets"], [{"target_id": "file-9", "target_type": "OBJECT"}])
        self.assertEqual(packet.relations[0].endpoints[1].entity_id, "file-9")
        self.assertEqual(validate_packet(packet).disposition, Disposition.STRUCTURAL)


if __name__ == "__main__": unittest.main()

from dataclasses import replace
import importlib
from pathlib import Path
import unittest

v11 = importlib.import_module("ethos" + "_structural_evidence")
v12 = importlib.import_module("ethos" + "_structural_evidence_v12")
producer = importlib.import_module("ethos" + "_execution_producer_research")


def scope(run: str, session: str):
    return v11.Scope((v11.ScopeSegment("RUN", run), v11.ScopeSegment("SESSION", session)))


def record(**changes):
    values = dict(
        packet_id="packet-1", proposal_id="proposal-1", proposal_scope=scope("r", "proposal"),
        execution_id="execution-1", execution_scope=scope("r", "execution"),
        proposal_assertor_id="proposal-assertor", proposal_assertor_scope=scope("r", "proposal-assertor"),
        execution_assertor_id="execution-assertor", execution_assertor_scope=scope("r", "execution-assertor"),
        proposal_source_instance_id="proposal-source", execution_source_instance_id="execution-source",
        reference_source_instance_id="reference-source", proposal_role_relation_id="proposal-role",
        execution_role_relation_id="execution-role", reference_relation_id="execution-references-proposal",
        proposal_role_assertion_id="proposal-role-claim", execution_role_assertion_id="execution-role-claim",
        reference_assertion_id="reference-claim", proposal_assertion_time="2026-09-16T00:00:00Z",
        proposal_availability_time="2026-09-16T00:00:00Z", execution_assertion_time="2026-09-16T00:00:00Z",
        execution_availability_time="2026-09-16T00:00:00Z", reference_assertion_time="2026-09-16T00:00:00Z",
        reference_availability_time="2026-09-16T00:00:00Z", availability_phase="PROPOSAL",
    )
    values.update(changes)
    return producer.ExplicitExecutionRecord(**values)


class ExplicitExecutionProducerTests(unittest.TestCase):
    def test_explicit_chain_is_structural_and_canonical(self):
        packet = producer.produce_execution_claim(record())
        self.assertEqual(v12.validate_packet(packet).disposition, v11.Disposition.STRUCTURAL)
        self.assertEqual(packet.verifications, ())
        self.assertEqual({(r.relation_type, r.relation_id) for r in packet.relations}, {
            ("HAS_EVENT_ROLE", "proposal-role"), ("HAS_EVENT_ROLE", "execution-role"),
            ("REFERENCES_PROPOSAL", "execution-references-proposal"),
        })
        text = v11.canonical_json(packet)
        self.assertEqual(text, v11.canonical_json(v11.from_canonical_json(text)))
        self.assertEqual(text, v11.canonical_json(producer.produce_execution_claim(record())))

    def test_actor_is_explicit_and_separate_from_assertors(self):
        packet = producer.produce_execution_claim(record(
            execution_actor_id="actor", execution_actor_scope=scope("r", "actor"),
            execution_actor_relation_id="actor-participates",
        ))
        self.assertEqual(v12.validate_packet(packet).disposition, v11.Disposition.STRUCTURAL)
        participants = {item.entity_id for item in packet.entities if item.entity_type == "PARTICIPANT"}
        self.assertEqual(participants, {"proposal-assertor", "execution-assertor", "actor"})
        actor_relation = next(item for item in packet.relations if item.relation_id == "actor-participates")
        self.assertEqual(tuple((item.role, item.entity_id) for item in actor_relation.endpoints),
                         (("participant", "actor"), ("event", "execution-1")))

    def test_scopes_replay_conflicts_and_identity_collapse(self):
        first = producer.produce_execution_claim(record())
        second = producer.produce_execution_claim(record(packet_id="packet-2", proposal_scope=scope("r", "other")))
        self.assertNotEqual(next(e for e in first.entities if e.entity_id == "proposal-1").scope,
                            next(e for e in second.entities if e.entity_id == "proposal-1").scope)
        with self.assertRaises(ValueError):
            producer.produce_execution_claim(record(execution_id="proposal-1"))
        replay = v11.EvidencePacket("replay", first.entities, first.relations + (first.relations[-1],), first.assertions)
        self.assertEqual(v12.validate_packet(replay).disposition, v11.Disposition.STRUCTURAL)
        conflicting = producer.produce_execution_claim(record(proposal_id="proposal-2", proposal_role_relation_id="proposal-role-2",
            proposal_role_assertion_id="proposal-role-claim-2", reference_relation_id="execution-references-proposal-2",
            reference_assertion_id="reference-claim-2"))
        combined = v11.EvidencePacket("combined", first.entities + conflicting.entities, first.relations + conflicting.relations,
                                      first.assertions + conflicting.assertions)
        self.assertEqual(v12.validate_packet(combined).disposition, v11.Disposition.STRUCTURAL)
        collision = replace(conflicting.relations[-1], relation_id="execution-references-proposal")
        bad = v11.EvidencePacket("bad", first.entities + conflicting.entities, first.relations + conflicting.relations[:-1] + (collision,),
                                 first.assertions + conflicting.assertions)
        self.assertEqual(v12.validate_packet(bad).disposition, v11.Disposition.REJECTED)

    def test_same_session_and_explicit_temporal_values_are_not_reordered(self):
        shared = scope("r", "shared")
        packet = producer.produce_execution_claim(record(
            proposal_scope=shared, execution_scope=shared,
            proposal_assertion_time="2026-09-17T00:00:00Z",
            proposal_availability_time="2026-09-17T00:00:00Z",
            execution_assertion_time="2026-09-16T00:00:00Z",
            execution_availability_time="2026-09-16T00:00:00Z",
            reference_assertion_time="2026-09-16T00:00:00Z",
            reference_availability_time="2026-09-16T00:00:00Z",
        ))
        self.assertEqual(v12.validate_packet(packet).disposition, v11.Disposition.STRUCTURAL)
        self.assertEqual(packet.assertions[0].assertion_time, "2026-09-17T00:00:00Z")
        self.assertEqual(packet.assertions[1].assertion_time, "2026-09-16T00:00:00Z")

    def test_missing_or_invalid_caller_data_fails_before_production(self):
        for changes in (
            {"packet_id": ""}, {"proposal_id": ""}, {"execution_id": ""}, {"proposal_scope": None},
            {"execution_scope": None}, {"proposal_assertor_id": ""}, {"proposal_source_instance_id": ""},
            {"proposal_assertion_time": "not-time"}, {"availability_phase": "NOT_A_PHASE"}, {"execution_actor_id": "actor"},
            {"execution_actor_id": "actor", "execution_actor_scope": scope("r", "actor")},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                producer.produce_execution_claim(record(**changes))

    def test_opaque_text_never_changes_the_structural_chain(self):
        packet = producer.produce_execution_claim(record(opaque_metadata={
            "text": "SUCCEEDED FAILED COMPLETED authorization gate target observation verification",
            "payload": {"actor": "not an identity", "result": "not an outcome"},
        }))
        self.assertEqual(v12.validate_packet(packet).disposition, v11.Disposition.STRUCTURAL)
        self.assertEqual(packet.assertions[-1].opaque_metadata.as_dict()["text"],
                         "SUCCEEDED FAILED COMPLETED authorization gate target observation verification")
        self.assertEqual({r.relation_type for r in packet.relations},
                         {"HAS_EVENT_ROLE", "REFERENCES_PROPOSAL"})

    def test_gate_words_and_malformed_support_do_not_create_or_repair_facts(self):
        allow = producer.produce_execution_claim(record(opaque_metadata={"gate": "ALLOW"}))
        block = producer.produce_execution_claim(record(packet_id="packet-block", opaque_metadata={"gate": "BLOCK"}))
        self.assertEqual(v11.canonical_json(allow.relations), v11.canonical_json(block.relations))
        without_proposal_role = v11.EvidencePacket("missing-role", allow.entities, allow.relations[1:], allow.assertions[1:])
        self.assertEqual(v12.validate_packet(without_proposal_role).disposition, v11.Disposition.QUARANTINED)
        malformed_role = replace(allow.relations[0], qualifiers=(v11.Qualifier("EVENT_ROLE", "EXECUTION"),))
        malformed = v11.EvidencePacket("malformed-role", allow.entities,
                                       (malformed_role,) + allow.relations[1:], allow.assertions)
        self.assertEqual(v12.validate_packet(malformed).disposition, v11.Disposition.QUARANTINED)

    def test_duplicate_assertion_and_divergent_assertion_id_follow_v12_rules(self):
        packet = producer.produce_execution_claim(record())
        replay = v11.EvidencePacket("assertion-replay", packet.entities, packet.relations,
                                    packet.assertions + (packet.assertions[-1],))
        self.assertEqual(v12.validate_packet(replay).disposition, v11.Disposition.STRUCTURAL)
        divergent = replace(packet.assertions[-1], source_instance_id="other-source")
        bad = v11.EvidencePacket("assertion-collision", packet.entities, packet.relations,
                                 packet.assertions[:-1] + (packet.assertions[-1], divergent))
        self.assertEqual(v12.validate_packet(bad).disposition, v11.Disposition.REJECTED)

    def test_test_only_isolation(self):
        root = Path(__file__).parent
        for path in root.glob("*.py"):
            if path.name in {Path(__file__).name, "ethos_execution_producer_research.py"}:
                continue
            self.assertNotIn("ethos_execution_producer_research", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

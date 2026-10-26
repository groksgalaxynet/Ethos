"""Research-only tests for the non-integrated Wrath characterization."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ethos_controller import ControllerSnapshot
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore
from wrath_measurement_research import CORPUS, CORPUS_V2, CORPUS_V3, DIMENSIONS, DIMENSIONS_V1, MEASUREMENT_LABELS, characterize, collision_report, measure


class WrathMeasurementResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        self.corpus_v2 = json.loads(CORPUS_V2.read_text(encoding="utf-8"))
        self.corpus_v3 = json.loads(CORPUS_V3.read_text(encoding="utf-8"))

    def test_corpus_schema_ids_and_determinism(self) -> None:
        cases = self.corpus["cases"]
        self.assertGreaterEqual(len(cases), 35)
        self.assertEqual(len({case["case_id"] for case in cases}), len(cases))
        self.assertTrue(all(set(case["labels"]) == set(DIMENSIONS) for case in cases))
        self.assertTrue(all(set(case["labels"].values()) <= MEASUREMENT_LABELS for case in cases))
        self.assertEqual(self.corpus["reviewer"], "PROJECT_REVIEW_V1")
        self.assertEqual(self.corpus["source"], "WRATH_MEASUREMENT_CONTRACT_V1")
        self.assertEqual(characterize(self.corpus), characterize(self.corpus))

    def test_context_and_provenance_suppressions(self) -> None:
        cases = {case["case_id"]: case for case in self.corpus["cases"]}
        self.assertEqual(measure(cases["quote-hpv"]["proposal"])["HPV"]["status"], "SUPPRESSED")
        self.assertEqual(measure(cases["reject-esi"]["proposal"])["ESI"]["status"], "SUPPRESSED")
        self.assertEqual(measure(cases["key-hpv"]["proposal"])["HPV"]["status"], "SUPPRESSED")
        self.assertEqual(measure(cases["value-hpv"]["proposal"])["HPV"]["status"], "DETECTED")
        self.assertEqual(measure(cases["control-resolution"]["proposal"])["ESI"]["status"], "NOT_DETECTED")

    def test_dimensions_are_separate_and_overlap_without_score(self) -> None:
        cases = {case["case_id"]: case for case in self.corpus["cases"]}
        self.assertEqual(measure(cases["esi-retaliate"]["proposal"])["HPV"]["status"], "NOT_DETECTED")
        all_three = measure(cases["overlap-all"]["proposal"])
        self.assertEqual({key: value["status"] for key, value in all_three.items()}, {key: "DETECTED" for key in DIMENSIONS})
        report = characterize(self.corpus)
        self.assertEqual(report["case_count"], len(self.corpus["cases"]))
        self.assertIn("overlap-all", report["cross_dimension_overlaps"])
        self.assertEqual(report["summary"]["ESI"]["lexical_misses"], [])
        source = Path(__file__).with_name("wrath_measurement_research.py").read_text(encoding="utf-8")
        for forbidden in ("RegulatorAnalysis", "overall_score", "tolerance", "EthosProposalGate", "ethos_controller", "subprocess"):
            self.assertNotIn(forbidden, source)

    def test_gate_controller_and_persistence_remain_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            evidence = Path(root) / "evidence.jsonl"
            gate = EthosProposalGate(JsonlEvidenceStore(evidence))
            decision = gate.inspect({"agent_id":"wrath-test","session_id":"wrath-test","task":"harm the target","proposal_type":"respond","target":"chat","arguments":{},"exposed_reasoning":"visible","raw_model_output":"{}","timestamp":"2026-09-14T00:00:00+00:00"})
            self.assertEqual(decision.decision, "ALLOW")
            before = evidence.read_bytes()
            ControllerSnapshot.from_gate_result(decision)
            measure({"task":"harm the target"})
            self.assertEqual(evidence.read_bytes(), before)
            self.assertEqual(ControllerSnapshot.from_gate_result(decision).unsupported_regulators["wrath"], "UNSUPPORTED")

    def test_v2_preserves_v1_and_detects_bounded_paraphrase_families(self) -> None:
        self.assertEqual(self.corpus_v2["preserves_v1_case_count"], 40)
        self.assertGreaterEqual(len(self.corpus_v2["cases"]), 70)
        self.assertEqual(self.corpus_v2["cases"][:40], self.corpus["cases"])
        cases = {case["case_id"]: case for case in self.corpus_v2["cases"]}
        for case_id, dimension in (("v2-esi-direct", "ESI"), ("v2-hpv-direct", "HPV"), ("v2-faf-direct", "FAF")):
            self.assertEqual(measure(cases[case_id]["proposal"])[dimension]["status"], "DETECTED")
        self.assertEqual(measure(cases["v2-esi-quote"]["proposal"])["ESI"]["status"], "SUPPRESSED")
        self.assertEqual(measure(cases["v2-hpv-prevent"]["proposal"])["HPV"]["status"], "SUPPRESSED")
        self.assertEqual(measure(cases["v2-faf-negation"]["proposal"])["FAF"]["status"], "SUPPRESSED")

    def test_v2_collision_report_and_v1_vocabulary_behavior(self) -> None:
        report = characterize(self.corpus_v2)
        collision = collision_report(self.corpus_v2)
        self.assertEqual(report["case_count"], 72)
        self.assertIn("v2-all-advocacy", collision["wrath_overlap_cases"])
        self.assertIn("v2-hpv-active", collision["active_overlap_cases"])
        self.assertIn("v2-faf-active", collision["active_overlap_cases"])
        known_miss = {"task": "make retaliation worse"}
        self.assertEqual(measure(known_miss, DIMENSIONS_V1)["ESI"]["status"], "NOT_DETECTED")
        self.assertEqual(measure(known_miss)["ESI"]["status"], "DETECTED")

    def test_v3_preserves_v2_pairs_and_baseline_schema(self) -> None:
        self.assertEqual(self.corpus_v3["preserves_v2_case_count"], 72)
        self.assertEqual(self.corpus_v3["cases"][:72], self.corpus_v2["cases"])
        self.assertGreaterEqual(len(self.corpus_v3["cases"]), 120)
        ids = {case["case_id"] for case in self.corpus_v3["cases"]}
        self.assertTrue(all(case.get("counterfactual_partner") in ids for case in self.corpus_v3["cases"][72:]))
        cases = {case["case_id"]: case for case in self.corpus_v3["cases"]}
        self.assertEqual(measure(cases["v3-escalation_boundary-discussion"]["proposal"])["ESI"]["status"], "NOT_DETECTED")
        self.assertEqual(measure(cases["v3-escalation_boundary-advocacy"]["proposal"])["ESI"]["status"], "DETECTED")
        baseline = json.loads((CORPUS_V3.parent / "wrath_measurement_characterization_v3_baseline.json").read_text())
        post = json.loads((CORPUS_V3.parent / "wrath_measurement_characterization_v3.json").read_text())
        self.assertEqual(baseline["case_count"], 120)
        self.assertEqual(post["baseline_comparison"]["changed_cases"], [])


if __name__ == "__main__":
    unittest.main()

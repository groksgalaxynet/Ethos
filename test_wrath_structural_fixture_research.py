import ast
import unittest

from wrath_structural_fixture_research import NOT_REPRESENTABLE, build_fixture, load_matrix, run_experiment


class WrathStructuralFixtureResearchTests(unittest.TestCase):
    def test_frozen_matrix_runs_once_with_all_expected_categories(self):
        report = run_experiment()
        self.assertEqual(report["case_count"], 28)
        self.assertTrue(report["all_pass"])
        self.assertFalse(report["semantic_leakage"])
        self.assertEqual({key: value["total"] for key, value in report["summary"].items()}, {"ESI": 7, "HPV": 7, "FAF": 7, "GUARDS": 7})

    def test_determinism_temporal_and_unknown_guards(self):
        first, second = run_experiment(), run_experiment()
        self.assertEqual(first, second)
        rows = {row["id"]: row for row in first["rows"]}
        self.assertEqual(rows["E07"]["STRUCTURE_ONLY"]["ESI"], NOT_REPRESENTABLE)
        self.assertEqual(rows["E07"]["later_STRUCTURE_ONLY"]["ESI"], NOT_REPRESENTABLE)  # no frozen local relation recovery
        self.assertEqual(rows["H04"]["STRUCTURE_ONLY"]["HPV"], NOT_REPRESENTABLE)
        self.assertEqual(rows["F03"]["STRUCTURE_ONLY"]["FAF"], NOT_REPRESENTABLE)

    def test_records_are_conformant_and_contain_no_shared_wrath_predicates(self):
        banned = {"wrath", "esi", "hpv", "faf", "aggression", "retaliation", "escalation", "coercion", "harmful", "excessive", "disproportionate", "violation"}
        for partition, cases in load_matrix()["partitions"].items():
            for case in cases:
                fixture = build_fixture(case, partition)
                values = []
                for relation in fixture.packet.relations:
                    values.append(relation.relation_type)
                    values.extend(endpoint.role for endpoint in relation.endpoints)
                self.assertFalse(any(token in " ".join(values).lower() for token in banned))

    def test_test_only_module_has_no_production_imports(self):
        tree = ast.parse(open("wrath_structural_fixture_research.py", encoding="utf-8").read())
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        self.assertFalse({"ethos_proposal_gate", "ethos_controller", "main_app", "ethos_evidence_view"} & imported)


if __name__ == "__main__": unittest.main()

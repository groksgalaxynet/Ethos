import unittest
from datetime import datetime, timezone

from ethos_phase5f_evidence_producers import categorical_benign, incentive_choice, resource_choice, wrath_write_evidence
from ethos_remaining_regulators_v2 import evaluate_gluttony, evaluate_lust, evaluate_lust_categorical, evaluate_wrath


class Phase5FEvidenceProducerTests(unittest.TestCase):
    def test_all_producers_run_existing_classifiers_non_enforcing(self):
        at = datetime.now(timezone.utc).isoformat()
        wrath = evaluate_wrath(**wrath_write_evidence("w"))
        gluttony = evaluate_gluttony(**resource_choice("g", at))
        contextual = evaluate_lust(**incentive_choice("l", at))
        categorical = evaluate_lust_categorical(**categorical_benign("c"))
        self.assertEqual([item.enforcement for item in (wrath, gluttony, contextual, categorical)], ["NONE"] * 4)
        self.assertEqual(wrath.state, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(gluttony.state, "NOT_INDICATED")
        self.assertEqual(contextual.state, "CANDIDATE")
        self.assertEqual(categorical.state, "NOT_INDICATED")


if __name__ == "__main__": unittest.main()

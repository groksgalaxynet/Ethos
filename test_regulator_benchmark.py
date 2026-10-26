import json, unittest
from pathlib import Path
from regulator_benchmark import cases, run, report
class BenchmarkTests(unittest.TestCase):
 def test_schema_ids_pairs_and_determinism(self):
  a,b=run(),run(); self.assertEqual(a,b); xs=a["cases"]; self.assertEqual(len({x["case_id"] for x in xs}),len(xs)); self.assertTrue(all(x["pair_id"] is None or sum(y["pair_id"]==x["pair_id"] for y in xs)>1 for x in xs))
 def test_metrics_controls_and_mixed_evidence(self):
  d=run(); r=report(d); self.assertEqual(r["summary"]["total"],len(d["cases"])); self.assertTrue(any(x["classification"]=="REVIEW_ONLY" for x in d["cases"])); self.assertTrue(any("mixed" in x["category"] for x in d["cases"]))
 def test_no_executor(self):
  s=Path(__file__).with_name("regulator_benchmark.py").read_text(); self.assertNotIn("subprocess",s); self.assertNotIn("Ollama",s)
if __name__=="__main__": unittest.main()

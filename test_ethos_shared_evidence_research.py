import unittest
from pathlib import Path
import json
from shared_evidence_characterization import FIXTURES, characterize
from ethos_shared_evidence_research import *
class SharedEvidenceTests(unittest.TestCase):
 def atom(self,**k): return EvidenceAtom(Field.PROVENANCE,"QUOTATION",ObservationState.OBSERVED,Source.PARSER_OBSERVATION,VerificationState.NOT_APPLICABLE,"r",**k)
 def test_valid_unknown_and_immutable(self):
  a=EvidenceAtom(Field.PROVENANCE,"UNKNOWN",ObservationState.UNKNOWN,Source.UNKNOWN_SOURCE,VerificationState.UNKNOWN,None); self.assertEqual(a.to_dict()["value"],"UNKNOWN")
  with self.assertRaises(Exception): a.value="x"
 def test_validation(self):
  with self.assertRaises(ValueError): EvidenceAtom(Field.PROVENANCE,"ADVOCATE",ObservationState.OBSERVED,Source.RAW_INPUT,VerificationState.ASSERTED,"x")
  with self.assertRaises(ValueError): EvidenceAtom(Field.PROVENANCE,"QUOTATION",ObservationState.UNKNOWN,Source.RAW_INPUT,VerificationState.ASSERTED,"x")
 def test_views_conflicts_and_determinism(self):
  a=self.atom(); b=EvidenceAtom(Field.PROVENANCE,"DIRECT_PROPOSAL",ObservationState.OBSERVED,Source.VERIFIED_EXTERNAL_EVIDENCE,VerificationState.VERIFIED,"v")
  self.assertFalse(views([a,a])[0].conflict); v=views([b,a])[0]; self.assertTrue(v.conflict); self.assertEqual(v,views([a,b])[0]); self.assertEqual(len(v.atoms),2)
 def test_no_policy_surface(self):
  source=Path(__file__.replace('test_','')).read_text()
  for word in ('ALLOW','BLOCK','score','tolerance','threshold','policy'): self.assertNotIn(word,source)
 def test_fixture_characterization_is_deterministic(self):
  data=json.loads(FIXTURES.read_text()); out=characterize(data); self.assertEqual(len(data['groups']),30); self.assertEqual(out,characterize(data)); self.assertTrue(out['rejected_atoms']); self.assertTrue(out['conflict_groups']); self.assertGreater(out['unknown_atoms'],0)
 def test_references_survive_views(self):
  out=characterize(json.loads(FIXTURES.read_text())); self.assertTrue(any(a['evidence_reference']=='ref-0' for _,v in out['views'] for a in v['atoms']))
if __name__=='__main__': unittest.main()

import hashlib, json, unittest
from pathlib import Path
from sloth_lexical_family_characterization import ROOT, evaluate

class SlothLexicalFamilyTests(unittest.TestCase):
 def setUp(self): self.data=json.loads((ROOT/'sloth_lexical_family_fixtures_v1.json').read_text())
 def test_schema_ids_and_family_distinction(self):
  cases=self.data['cases']; self.assertEqual(len(cases),50); self.assertEqual(len({x['case_id'] for x in cases}),50); self.assertTrue(all(x['family_id'] in self.data['families'] for x in cases)); self.assertEqual({x['expected'] for x in cases},{'POSITIVE','NON_POSITIVE'}); self.assertTrue({x['observability'] for x in cases} <= {'TEXT_OBSERVABLE','CONTEXT_REQUIRED','EXTERNAL_EVIDENCE_REQUIRED'}); self.assertEqual(len(self.data['families']),5)
 def test_unsupported_owner_removal_cases_remain_non_positive(self):
  cases=[x for x in self.data['cases'] if x['family_id']=='RAF_OWNER_REMOVAL']; self.assertEqual(len(cases),10); self.assertTrue(all(x['expected']=='NON_POSITIVE' for x in cases))
 def test_blind_corpus_unchanged(self):
  raw=json.loads((ROOT/'sloth_blind_challenge_corpus_v1.json').read_text()); fingerprint=raw.pop('canonical_sha256'); self.assertEqual(hashlib.sha256(json.dumps(raw,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),fingerprint)
if __name__=='__main__': unittest.main()

# ETHOS++ GitHub Publication Audit

Prepared locally on 2026-10-26. No GitHub authentication, fetch, pull, push,
commit, credential change, model invocation, or development-source write was
performed for this publication preparation.

## Authoritative V1 baseline

The local checkout contains 359 non-Git files. Its proposed non-ignored
publication set contains 359 files: 292 of 303 historical manifest paths, 39
V2 selected paths, and 28 publication/support paths. Eleven historical
manifest paths are intentionally withheld: the nine path-bearing files listed
below and two Ollama summaries.

The authoritative source is the development baseline identified by:

- `ETHOS_V1_FROZEN_MANIFEST.sha256` — 303 recorded paths;
- `ETHOS_V1_VERIFICATION.md` — identifies `python3 -m unittest discover -v`
  as the canonical historical runner;
- `ETHOS_V1_SYSTEM_FREEZE_READINESS_AUDIT.md` and related locked checkpoint
  material — delimit the production, shadow, and legacy surfaces.

The development source passed the existing manifest verification before any
transfer. The checkout then passed `sha256sum -c
ETHOS_V1_FROZEN_MANIFEST.sha256`: **303 / 303 files matched** before the
privacy cleanup. The historical manifest was copied but not regenerated and is
preserved byte-for-byte. `ETHOS_V1_PUBLICATION_MANIFEST.sha256` contains the
unchanged historical hash lines for the 292 publishable files. It is a
public-subset verification manifest; it does not replace or redefine the
303-file historical frozen baseline.

### Previously differing overlap paths

The nine shared files below differed between the old checkout and the frozen
development baseline. The manifest-verified development versions are the
authoritative V1 versions and replaced the old checkout copies:

1. `ETHOS_FILE_MAP.md`
2. `ETHOS_NEXT.md`
3. `ETHOS_RUNTIME_CONTRACT.md`
4. `envy_analyzer.py`
5. `ethos_cli.py`
6. `ethos_proposal_gate.py`
7. `greed_analyzer.py`
8. `main_app.py`
9. `pride_analyzer.py`

No uncertain V1 content was chosen by judgment: every transferred V1 path is
byte-verified against the existing authority manifest.

## V1 inventory and prior missing-path classification

All 276 previously missing frozen paths were present for the pre-cleanup local
historical verification. The 303-file historical inventory is preserved in the
read-only development source; the public checkout intentionally retains 292
manifest files:

| Classification | Count | Publication treatment |
| --- | ---: | --- |
| Source code (including retained legacy/GUI/research support) | 111 | 108 included unchanged; 3 path-bearing utility scripts withheld |
| Tests | 61 | Included unchanged; not all run for this preparation |
| Documentation, contracts, and JSON design records | 65 | 59 included unchanged; 6 path-bearing documentation files withheld |
| Versioned evidence, fixtures, corpora, and reports | 66 | 64 allowlisted for publication; 2 Ollama summaries withheld and removed from the public checkout |

The V1 fixture/evidence group contains versioned baseline, characterization,
Sloth, and Wrath records. It does not include JSONL runtime streams, SQLite
ledgers, model weights, or archives. The two withheld manifest entries are
`evidence/ollama_evaluation/evaluation_summary.json` and
`evidence/ollama_evaluation/evaluation_summary.md`. The JSON file contains an
absolute development-machine path; the Markdown summary is not required for
the focused reproducibility checks. Neither file is altered or deleted in the
read-only source; both are removed from the public checkout inventory.

### Frozen machine-specific path audit

Nine manifest-listed frozen files contain 12 occurrences of an absolute
development-machine prefix. They are excluded from the public checkout under
the owner's privacy decision. Each occurrence is machine-specific metadata,
not a credential or token:

| File | Occurrences | Sensitivity classification |
| --- | ---: | --- |
| `ETHOS_RUNTIME_ACTION_CONTEXT_PRODUCER_V1.md` | 2 | Documentation link to local development path |
| `ETHOS_RUNTIME_ASSIGNMENT_PRODUCER_V1.md` | 2 | Documentation link to local development path |
| `ETHOS_RUNTIME_DECISION_RECORDER_V1.md` | 2 | Documentation link to local development path |
| `ETHOS_SLOTH_LIVE_SHADOW_READINESS_REVIEW.md` | 1 | Documentation link to local development path |
| `ETHOS_SLOTH_REAL_OBSERVATION_RUN_V1.md` | 1 | Documentation link to local development path |
| `ETHOS_SLOTH_SHADOW_CALIBRATION_PLAN_V1.md` | 1 | Documentation link to local development path |
| `cleanup_scripts_archive.py` | 1 | Hard-coded local development path |
| `ethos_file_inventory.py` | 1 | Hard-coded local development path |
| `ethos_reference_audit.py` | 1 | Hard-coded local development path |

The withheld Ollama JSON summary contains one additional absolute local path,
but is not part of the 292-file public subset. No published source or test
imports any of the nine withheld files. The three utility scripts reference
only one another; the remaining references are documentation/audit mentions,
including one nonfunctional historical supersession note.

## V2 Phase 5A–5H release slice

The V2 slice contains 21 V2-specific source modules, 13 focused tests, the
Phase 5F checkpoint, the Phase 5G and 5H reports, and two reviewed synthetic
fixtures. Its import closure was checked across 39 local modules; 18 shared
dependencies are supplied by the now-published V1 baseline.

The V2-specific source includes:

- generic configuration, append-only observation, canonicalization, review,
  and runtime-runner modules;
- receipt observation, allowlisted local receipt boundary, llama.cpp request
  adapter, and dual-side provenance modules;
- Wrath, Gluttony, and two Lust research evaluators/adapters;
- Phase 5F, 5G, and 5H evidence/calibration/demo support; and
- the read-only V2 presentation adapter required by the focused V2 tests.

The checked-in V2 fixture files are:

- `evidence/phase5g_calibration_dataset_v1.json`
- `evidence/phase5h_w07_corrected_fixture_v1.json`

Both declare `SYNTHETIC_FIXTURE` provenance. They are not runtime receipts or
human labels.

## Documentation and dependency changes

| Path | Action |
| --- | --- |
| `README.md` | Rewritten for the actual V1/V2 publication boundary, limited evaluation permission, local procedures, limitations, and evidence claims |
| `README_HISTORICAL_PREPUBLICATION.md` | Added clearly labeled pre-publication README reference; not a statement of current functionality |
| `ETHOS_V1_PUBLICATION_MANIFEST.sha256` | Added unchanged hash lines for the 292 privacy-reviewed V1 files selected for public verification; does not replace the 303-file historical manifest |
| `ETHOS_PUBLICATION_ARCHITECTURE.md` | Added source-level V1 production / V2 shadow architecture |
| `ETHOS_GITHUB_PUBLICATION_AUDIT.md` | Added this exact inventory, verification record, and blocker list |
| `.gitignore` | Updated to an exact reviewed-evidence allowlist; excludes secrets, runtime state, weights, backups, archives, the two Ollama summaries, and nine explicitly named path-bearing frozen files |
| `Requirements.txt` | Documents Qt and the optional FastAPI dependency; V2 core uses the standard library |
| `LICENSE.md` | Revised to a proprietary limited-evaluation license; no open-source license was added |

## Explicit exclusions

The following development material remains excluded:

- credentials, `.env*`, keys, certificates, token/credential-named files;
- JSONL observations, authorizations, requests, receipts, reviews, live runs,
  disposable targets, local telemetry, SQLite databases, logs, and runtime
  state;
- model weights and downloaded assets (`.gguf`, `.safetensors`, `.pt`, `.pth`,
  `.ckpt`, `.onnx`);
- backups, archives, virtual environments, caches, and historical phase
  artifact directories;
- unreviewed development-only code and data outside the V1 manifest and V2
  import/test closure.
- the two manifest-listed Ollama evaluation summaries described above, pending
  explicit owner review of their publication status.
- the nine path-bearing frozen files listed in the machine-specific path audit;
  they were removed from this public checkout only and remain in the read-only
  historical development source.

## Focused verification results

| Check | Result |
| --- | --- |
| Development V1 manifest check | PASS — 303 recorded files matched before transfer |
| Historical V1 manifest check | PASS before privacy cleanup — 303 / 303 files matched in the preserved historical source/copy; the public checkout deliberately omits 11 of those paths |
| Public V1 subset manifest check | PASS — 292 / 292 publishable V1 files matched `ETHOS_V1_PUBLICATION_MANIFEST.sha256` |
| V2 source syntax and imports | PASS — 39-module local closure |
| Focused V2 tests | PASS — 52 tests across observation, runner, receipt, authorization, provenance, Phase 5F/5G/5H, Gluttony, Lust, and V2 adapter modules |
| Generic-shadow production-gate isolation test | PASS |
| Documentation whitespace check | PASS |
| Credential/generated audit | PASS with exclusions — no credential literal, `.env`, key/certificate, JSONL, DB, model-weight, or archive file is allowlisted; ten absolute-path files were withheld from the public subset |
| Git staged-file check | PASS — no files are staged; excluded files are not tracked by this checkout and are protected by `.gitignore` |

No full historical regression was run. No live llama.cpp/API request or tool
execution demo was run during verification.

## Remaining blockers before a public commit

1. **Frozen V1 readiness caveats remain historical.** The V1 readiness audit
   records unresolved whole-system freeze issues around canonical historical
   regression accounting, legacy radar/kernel isolation, and Sloth duplicate
   accounting. This publication preserves those documents; it does not claim
   that they are resolved.
2. **Legacy optional module gap.** The frozen `ethos_imprint_gui.py` imports
   `ethos_imprint_gui_qt`, which is not present in the verified development
   baseline or manifest. It is retained historical material, not part of the
   focused production/V2 import closure. A future V1 maintenance decision is
   needed before claiming every retained legacy GUI module is import-complete.
3. **V2 is not production-ready.** It remains shadow-only, default-disabled,
   and `enforcement=NONE`. Its synthetic fixtures and bounded local records do
   not establish real-world behavioral calibration.
4. **Evidence-contract gaps remain.** Wrath needs independent harm, intent,
   authorization, target, timing, consequence, and proportionality evidence.
   Gluttony and Lust need their documented real-world ownership/objective/
   incentive/alternative evidence contracts.
5. **Historical/public-scope distinction.** Eleven historical V1 manifest
   entries are intentionally withheld. The 292-file public manifest makes the
   privacy-reviewed public subset reproducible, but it must not be described
   as a complete frozen historical baseline. The owner must accept that
   limitation or separately approve any withheld material.
6. **Rights review is advisable.** The revised limited-evaluation permission
   preserves prior-version permissions and disclaims rights in third-party
   components. No contributor agreement or third-party provenance review was
   found in the Git history inspected; PyQt6 and FastAPI remain subject to
   their own terms. Legal review is appropriate before a public release.
7. **Machine-specific historical paths.** Nine frozen files containing an
   absolute development path were removed from this public checkout and
   excluded from the public manifest. Two retained test files contain a
   `/tmp/` fixture literal. No credential literal was found. The public V1
   representation is therefore deliberately incomplete relative to the
   historical frozen baseline.

## Publication state

The checkout is **READY FOR OWNER APPROVAL**, not ready for publication. It is
uncommitted and no network operation has been used.

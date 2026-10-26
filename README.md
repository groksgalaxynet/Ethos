# ETHOS++

> Proprietary, limited-evaluation research material — **not open source**.
> Reviewers may clone and run the existing unmodified code and tests for
> non-commercial evaluation; they may not modify or redistribute it. See
> [LICENSE.md](LICENSE.md).

ETHOS++ investigates an inspectable, deterministic boundary for evaluating AI
action proposals from explicit evidence. It is experimental research. It does
not certify safety, alignment, legality, or suitability for deployment.

## Publication snapshot

This checkout contains two deliberately separated bodies of work:

| Layer | What is included | Enforcement |
| --- | --- | --- |
| Frozen V1 baseline | 303-file historical baseline verified in the read-only source; 292-file privacy-reviewed public subset verified by `ETHOS_V1_PUBLICATION_MANIFEST.sha256` | `EthosProposalGate` is the only production `ALLOW` / `BLOCK` authority; Greed, Pride, and Envy are its only integrated regulators |
| V2 research | Import-complete Phase 5A–5H shadow-observation closure, focused tests, reports, and synthetic fixtures | Permanently non-enforcing: all V2 results use `enforcement=NONE` |

The historical V1 source was verified before this public copy was prepared and
was not rewritten. Eleven manifest-listed files are intentionally withheld
from the proposed public set: nine contain absolute development-machine paths,
and two are Ollama evaluation summaries. The V2 generic observation layer and
runtime runner have no ProposalGate invocation or execution authority.

## Architecture

```text
V1 production proposal path
proposal ──> EthosProposalGate ──> ALLOW / BLOCK
                    │
                    └── Greed / Pride / Envy only

V2 research observation path
local request ──> independent authorization ──> isolated action boundary
                                                     │
                                                     ▼
                                              action receipt or denial
                                                     │
                                                     ▼
                                      runtime shadow runner (if enabled)
                                      ├── Wrath
                                      ├── Gluttony
                                      ├── Lust contextual incentive
                                      └── Lust categorical policy
                                                     │
                                                     ▼
                         append-only JSONL result / observation / review streams

All V2 outputs: enforcement=NONE; no path to ProposalGate or execution.
```

See [ETHOS_PUBLICATION_ARCHITECTURE.md](ETHOS_PUBLICATION_ARCHITECTURE.md) for
the source-level boundary and supported local procedures. The frozen historical
V1 architecture remains available unchanged in [ETHOS_ARCHITECTURE.md](ETHOS_ARCHITECTURE.md).
The superseded, pre-publication public README is retained as
[historical documentation](README_HISTORICAL_PREPUBLICATION.md), not as a
statement of current functionality.

## V1 baseline status

The authoritative V1 source is the manifest-backed 303-file historical
baseline in the read-only development source, not the prior GitHub checkout.
It was verified before this public copy was prepared. Eleven manifest-listed
files are withheld here: the two Ollama evaluation summaries and nine frozen
documentation/utility files containing absolute development-machine paths.
`ETHOS_V1_PUBLICATION_MANIFEST.sha256` contains the unchanged recorded hash
lines for the remaining 292 files and verifies this publicly reproducible
subset. That subset is **not** a complete frozen historical baseline. The
historical verification document records standard-library `unittest` discovery
as the canonical runner; this publication does not claim to reproduce its full
historical suite.

Only Greed, Pride, and Envy can affect the V1 production gate. Sloth is a
separate frozen shadow/calibration system. Wrath, Gluttony, and Lust are not
V1 production regulators. Legacy GUI/radar and other retained modules are
documented historical material, not an alternative production authority.
One retained legacy file, `ethos_imprint_gui.py`, imports an unavailable
`ethos_imprint_gui_qt` module; it is not part of the focused V1/V2 import
closure and is a disclosed publication limitation.

## V2 Phase 5A–5H research

- **5A:** reusable append-only JSONL results, observations, reviews,
  canonicalization, provenance, and duplicate handling.
- **5B:** independently configurable, default-disabled runtime shadow runner.
- **5C:** separate Lust contextual-incentive and categorical-policy branches.
- **5D–5F:** receipt observation, independent authorization, and append-only
  request-to-outcome provenance linkage.
- **5G:** 64 pre-labeled `SYNTHETIC_FIXTURE` cases, 16 for each research path.
  Reported controlled matches: Wrath 15/16, Gluttony 16/16, Lust contextual
  16/16, Lust categorical 16/16. The Wrath abstention was a contradictory
  fixture-evidence issue, not a classifier change.
- **5H:** a corrected W07 synthetic fixture, denied-attempt observation, and
  conservative target-state/telemetry evidence handling.

The published calibration fixtures are explicitly synthetic:

- [Phase 5G dataset](evidence/phase5g_calibration_dataset_v1.json)
- [Phase 5H corrected W07 fixture](evidence/phase5h_w07_corrected_fixture_v1.json)

Detailed bounded claims and limitations are in
[ETHOS_PHASE5G_CALIBRATION_REPORT.md](ETHOS_PHASE5G_CALIBRATION_REPORT.md)
and [ETHOS_PHASE5H_EVIDENCE_REPORT.md](ETHOS_PHASE5H_EVIDENCE_REPORT.md).

## Local setup and focused checks

Python 3.10+ is recommended. Install only the listed local dependencies if
you need Qt interfaces or the optional FastAPI sandbox module:

```bash
python3 -m pip install -r Requirements.txt
```

The V2 shadow closure uses only the Python standard library. It is
default-disabled and must not be pointed at production state. Focused,
network-free checks from the checkout root include:

```bash
python3 -m py_compile ethos_generic_shadow_observation.py ethos_runtime_shadow_runner.py ethos_remaining_regulators_v2.py
python3 -m unittest -v test_ethos_generic_shadow_observation test_ethos_runtime_shadow_runner test_ethos_phase5g_calibration test_ethos_phase5h_evidence
sha256sum -c ETHOS_V1_PUBLICATION_MANIFEST.sha256
```

The last command verifies the public 292-file subset. The historical
`ETHOS_V1_FROZEN_MANIFEST.sha256` remains unchanged and verifies all 303 files
only in the preserved historical source that also retains the eleven withheld
paths. Do not edit a manifest-listed file and then regenerate its hash. Do not
run the live challenge/demo modules unless you have an authorized, isolated
local environment; they are not needed for the focused checks above.

## Evidence boundaries and limitations

- Synthetic fixtures test existing classifier behavior under controlled inputs;
  they are not real-world calibration, prevalence, or safety proof.
- A local model request is not an execution claim. Only an isolated boundary's
  receipt establishes its limited recorded outcome.
- A reported disposable file action is a simulated-environment target. It does
  not establish real-world harm, intent, proportionality, resource ownership,
  necessity, incentive association, or relationship facts.
- Wrath needs independent harm, intent, timing, authorization, target, and
  proportionality evidence. Gluttony and both Lust paths need their documented
  independent evidence contracts before any broader calibration claim.
- No V2 result authorizes enforcement or promotion to V1.

Runtime receipts, local telemetry, databases, JSONL streams, model weights,
credentials, backups, and machine-specific files are intentionally excluded.
The exact inventory, eleven withheld historical paths, verification results,
and publication blockers are in [ETHOS_GITHUB_PUBLICATION_AUDIT.md](ETHOS_GITHUB_PUBLICATION_AUDIT.md).

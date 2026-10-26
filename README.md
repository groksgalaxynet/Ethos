# ETHOS++

> Proprietary, limited-evaluation research material — **not open source**.
> See [LICENSE.md](LICENSE.md) before cloning, running, or evaluating this
> repository.

ETHOS++ investigates an inspectable, deterministic boundary for evaluating AI
action proposals from explicit evidence. The research question is deliberately
narrow: how can proposed actions be assessed through recorded policy checks and
evidence without treating a proposal, a model response, or an experimental
observation as proof of real-world execution or safety?

It is experimental research. It does **not** certify safety, alignment,
legality, reliability, or suitability for deployment.

## Start here

| For | Read |
| --- | --- |
| A concise map of the repository | [Documentation index](DOCUMENTATION_INDEX.md) |
| System boundaries and decision paths | [Architecture guide](ARCHITECTURE.md) |
| Published V1/V2 boundary and local procedures | [Publication architecture](ETHOS_PUBLICATION_ARCHITECTURE.md) |
| Exact public inventory, exclusions, and checks | [Publication audit](ETHOS_GITHUB_PUBLICATION_AUDIT.md) |
| V1 verification history | [V1 verification record](ETHOS_V1_VERIFICATION.md) |
| Phase 5G/5H calibration claims and limits | [5G report](ETHOS_PHASE5G_CALIBRATION_REPORT.md) · [5H report](ETHOS_PHASE5H_EVIDENCE_REPORT.md) |
| Ownership and evaluation terms | [LICENSE.md](LICENSE.md) |

## Publication snapshot

This checkout deliberately separates a frozen historical production baseline
from non-enforcing research work.

| Layer | Included here | Authority and enforcement |
| --- | --- | --- |
| **V1 public subset** | 292 privacy-reviewed files verified by `ETHOS_V1_PUBLICATION_MANIFEST.sha256` | `EthosProposalGate` is the production proposal-decision authority. Only Greed, Pride, and Envy are integrated into its regulator decision path. |
| **V1 historical record** | A 303-file manifest preserved as `ETHOS_V1_FROZEN_MANIFEST.sha256` | The full historical baseline is not reproduced in this public subset. Eleven path/evidence files are intentionally withheld. |
| **V2 research** | Phase 5A–5H shadow observation, tests, reports, and reviewed synthetic fixtures | Default-disabled and permanently non-enforcing. Every V2 result uses `enforcement=NONE`. |

The original 303-file V1 baseline was verified before this public copy was
prepared and was not rewritten. The public subset intentionally excludes nine
frozen documentation/utility files that contained absolute development-machine
paths, plus two withheld Ollama evaluation summaries. The public subset is
reproducible, but it is **not** a complete frozen historical baseline.

## What is implemented

### V1 production governance

`EthosProposalGate` inspects an explicit proposal, applies bootstrap checks,
and evaluates the three production-integrated regulators:

- **Greed**
- **Pride**
- **Envy**

It produces an `ALLOW` or `BLOCK` decision record. An `ALLOW` is an approval
record, not execution authority. The gate may record bounded block history and
consequence metadata, but it does not itself execute proposed actions. See the
[V1 decision flow](ARCHITECTURE.md#v1-proposalgate-decision-flow) and
[production-regulator relationships](ARCHITECTURE.md#production-regulator-relationships).

Sloth is a separate frozen shadow/calibration system, not a production Gate
regulator. Legacy GUI/radar/kernel material is retained as historical context,
not as another production authority.

### V2 experimental shadow research

Phase 5A–5H adds reusable, append-only observation research around the existing
Wrath, Gluttony, and Lust classifiers:

- independent, default-disabled shadow configuration;
- JSONL result, observation, canonicalization, and human-review streams;
- provenance labels distinguishing `REAL_RUNTIME`, `SYNTHETIC_FIXTURE`, and
  `REPLAY`;
- a bounded runtime runner for Wrath, Gluttony, and both Lust branches;
- an isolated receipt/authorization boundary for local demonstrations; and
- reviewed synthetic calibration fixtures and reports.

V2 does not import or invoke ProposalGate as an enforcement route. It cannot
turn a classification into a production decision or action. See the
[shadow pipeline](ARCHITECTURE.md#v2-shadow-only-research-pipeline).

## Evidence and limitations

The published Phase 5 fixtures are explicitly synthetic:

- [Phase 5G calibration dataset](evidence/phase5g_calibration_dataset_v1.json)
- [Phase 5H corrected W07 fixture](evidence/phase5h_w07_corrected_fixture_v1.json)

Phase 5G reports controlled fixture matches of Wrath 15/16, Gluttony 16/16,
Lust contextual 16/16, and Lust categorical 16/16. The Wrath abstention was a
contradictory fixture-evidence issue, not a classifier change. These results
are bounded fixture results—not real-world prevalence, safety, or calibration
claims.

Important limits:

- A model request is not proof of execution; only an isolated boundary receipt
  establishes its limited recorded outcome.
- A disposable local file action is simulated-environment evidence, not proof
  of real-world harm, intent, proportionality, resource ownership, necessity,
  incentive association, or relationship facts.
- Wrath needs independent harm, intent, timing, authorization, target, and
  proportionality evidence. Gluttony and both Lust paths require their
  documented ownership/objective/incentive/alternative evidence contracts.
- No V2 result authorizes enforcement or promotion to V1.

For exact claims and caveats, read the [Phase 5G report](ETHOS_PHASE5G_CALIBRATION_REPORT.md),
[Phase 5H report](ETHOS_PHASE5H_EVIDENCE_REPORT.md), and
[publication audit](ETHOS_GITHUB_PUBLICATION_AUDIT.md).

## Local evaluation

Python 3.10+ is recommended. Install the listed local dependencies only if you
need Qt interfaces or the optional FastAPI sandbox module:

```bash
python3 -m pip install -r Requirements.txt
```

The V2 shadow closure uses only the Python standard library. It is
default-disabled and must not be pointed at production state. From the checkout
root, the focused, network-free checks are:

```bash
python3 -m py_compile ethos_generic_shadow_observation.py ethos_runtime_shadow_runner.py ethos_remaining_regulators_v2.py
python3 -m unittest -v test_ethos_generic_shadow_observation test_ethos_runtime_shadow_runner test_ethos_phase5g_calibration test_ethos_phase5h_evidence
sha256sum -c ETHOS_V1_PUBLICATION_MANIFEST.sha256
```

The final command verifies the public 292-file V1 subset. The historical
303-file manifest remains unchanged and can verify only an environment that
retains all historical entries. Do not edit a manifest-listed file and then
regenerate its hash. Live challenge/demo modules are not required for the
focused checks and should run only in an authorized, isolated local environment.

## Public-release boundary

Runtime receipts, local telemetry, databases, JSONL streams, model weights,
credentials, backups, and machine-specific files are intentionally excluded.
The [publication audit](ETHOS_GITHUB_PUBLICATION_AUDIT.md) records the exact
public inventory, eleven withheld historical paths, verification results, and
remaining publication limitations.

ETHOS++ is publicly inspectable under a limited evaluation permission; it is
not released under an open-source license. All rights not expressly granted
are reserved. See [LICENSE.md](LICENSE.md).

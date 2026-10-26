# ETHOS++ V1 System Freeze-Readiness Audit

> Historical finding superseded on 2026-10-05 by
> `ETHOS_V1_FREEZE_INTEGRITY_REMEDIATION.md`. Its three identified blockers
> were remediated without changing ProposalGate or Sloth enforcement.

Audit date: 2026-10-05. This is an evidence-only audit. No regulator, gate,
calibration artifact, fixture, or test was changed.

## Verdict

**ETHOS V1 FREEZE READINESS: NOT READY.**

The narrow ProposalGate path is regression-clean when run with its compatible
test runner, and Sloth remains isolated and non-enforcing. A truthful
whole-system V1 freeze cannot yet be declared because (1) the locked 428-test
baseline does not identify the currently passing test surface, and (2) a
retained legacy GUI/radar path computes a separate runtime `allowed` result
from all seven mutable GUI values. The latter permits Sloth, Wrath, Lust, and
Gluttony to influence a decision-like output outside ProposalGate.

## 1. Current test baseline

| Command | Result | Count / notes |
| --- | --- | --- |
| `python3 -m pytest -q` | Not collected | Global Dash pytest plugin crashes during startup (`importlib.metadata` returns `None` for Plotly). No project test ran. |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q` | Failed | **508 passed, 101 errors** in 323.69s. Pytest invokes `setup(directory)` on two `unittest.TestCase` modules with the module object, not their expected temporary directory. The affected modules are `test_ethos_runtime_action_context_producer.py` and `test_ethos_runtime_assignment_producer.py`; this is a runner-compatibility failure, not an assertion failure. |
| `python3 -m unittest discover -v` | Passed | **609 tests passed** in 298.610s. No failures, skips, or timeouts were reported. |
| `python3 ethos_sloth_shadow_calibration.py summary` | Completed | Raw streams contain two `REAL_RUNTIME` records, one review, and two total observations; see the calibration-integrity finding below. |
| `sha256sum ethos_structural_evidence.py test_ethos_structural_evidence.py` | Passed | Values match the frozen V1.1 values recorded in the Structural Evidence documents. |

The known Wrath research-fixture warning remains non-failing: the unittest run
reported a `ResourceWarning` for an unclosed source-file handle in
`test_wrath_structural_fixture_research.py`. It is unchanged in character
from the locked checkpoint and did not affect the result.

The locked Sloth checkpoint records **428 passed, 0 failed, 0 skipped, 0
timed out**. Current source has a larger test surface and no test-runner
configuration file was found. Therefore 609 passing tests is current evidence,
not proof that the locked 428-test surface was rerun unchanged.

## 2. Regulator inventory and status

| Regulator/domain | Current classification | Evidence and actual status |
| --- | --- | --- |
| Greed | `PRODUCTION / ENFORCING` | Headless `GreedAnalyzer` is invoked by `EthosProposalGate.inspect`; threshold violations can `BLOCK`. |
| Pride | `PRODUCTION / ENFORCING` | Headless `PrideAnalyzer` is invoked by the gate; threshold violations can `BLOCK`. |
| Envy | `PRODUCTION / ENFORCING` | Headless `EnvyAnalyzer` is invoked by the gate; threshold violations can `BLOCK`. |
| Sloth | `SHADOW / CALIBRATION` | `SLOTH_RESEARCH_EVALUATOR_V1` with threshold **2** and `enforcement = NONE`; shadow result, observation, and review streams have no gate import. |
| Wrath | `RESEARCH` | Characterization/fixture/structural experiments exist. No approved production analyzer, score, tolerance, policy, or gate path exists. |
| Lust | `SCAFFOLD ONLY` | Retained random/mutable legacy GUI and candidate labels; no accepted input contract, deterministic analyzer, tests, policy, or gate path. |
| Gluttony | `SCAFFOLD ONLY` | Retained random/mutable legacy GUI and candidate labels; no context contract, deterministic analyzer, collision rule, policy, or gate path. |

Shared components are present: `EthosProposalGate`; Greed/Pride/Envy evidence
views; append-only JSONL gate and Sloth streams; SQLite violation history and
scar persistence; `EthosController` read-only projections; read-only active
desktop views; Sloth shadow/review tooling; research corpora and fixtures; and
the retained legacy regulator GUI/radar shell. Research-only code also
includes Wrath measurement/structural experiments, Structural Evidence V1.1
and V1.2, factual-context work, and Sloth producers/evaluator.

## 3. Enforcement and ProposalGate matrices

### Actual decision paths

| Path / regulator | Input and evaluation | Can affect ProposalGate? | Actual effect | Default behavior |
| --- | --- | --- | --- | --- |
| Bootstrap policy | Explicit `ActionProposal` fields; malformed/type/bypass/self-modification/runtime checks | Yes | `ALLOW` or `BLOCK`; bootstrap precedes regulators | Fail closed for malformed/unknown/bypass/self-modification. Optional legacy-runtime rejection also blocks. |
| Greed | Proposal-visible source-addressed text -> deterministic scores/tolerances | Yes | `BLOCK` on violation | Fails safe through gate validation; no execution path. |
| Pride | Proposal-visible `social status` cue -> deterministic score/tolerance | Yes | `BLOCK` on violation | Same gate boundary. |
| Envy | Proposal-visible `social comparison` cue -> deterministic score/tolerance | Yes | `BLOCK` on violation | Same gate boundary. |
| Sloth shadow | Runtime-produced assignment, decision, and context records -> research evaluator -> shadow result/observation/review | No | Observe only; `NONE` enforcement | Missing/conflicting/non-comparable facts remain explicit rather than becoming a positive. |
| Wrath research | Research corpus/explicit neutral fixtures -> observation states | No | Research result only | No production policy decision. |
| Lust / Gluttony legacy GUIs | Mutable UI values/sliders/random simulation | No | No gate action | No accepted policy semantics. |
| Legacy radar/kernel | Seven GUI scalar values are averaged; `ethos.verify_request("Admin", ego=average)` also reads scar count for display | No | Separate `allowed`/`SYSTEM STABLE` or `DRIFT DETECTED` output and event log | Fails closed when `Admin` is unregistered; it has no executor or ProposalGate connection. |

`EthosProposalGate` evaluates Greed, then Pride, then Envy after bootstrap
checks. It preserves all violating policy IDs but uses that order for the
primary reason. A `BLOCK` may record history/scar metadata; a persistence
failure does not weaken the `BLOCK`. The gate records an approval only:
`execution = NOT_EXECUTED_TASK_1`.

### ProposalGate interaction matrix

| Component | Gate import/call | Can change gate decision | Gate evidence |
| --- | --- | --- | --- |
| Bootstrap policy | Internal | Yes | Checks and policy IDs |
| Greed / Pride / Envy | Direct analyzer calls | Yes | `regulators.greed`, `.pride`, `.envy` |
| Sloth | None | No | None |
| Wrath | None | No | None |
| Lust | None | No | None |
| Gluttony | None | No | None |
| Controller/read-only GUI | Reads a prior result/evidence only | No | No mutation |
| Legacy radar/kernel | Separate legacy runtime call | No | Separate runtime SQLite event only |

## 4. Isolation and coupling findings

1. **Sloth isolation is confirmed.** `ethos_sloth_shadow.py` and the
   calibration/observation tooling do not import or call ProposalGate, a
   production regulator, or an executor. A shadow failure or human review
   cannot create `ALLOW` or `BLOCK`.
2. **Wrath is isolated from production.** Its research modules and fixture
   experiments are not imported by ProposalGate or the controller.
3. **Lust and Gluttony are not ProposalGate inputs.** Their retained GUI
   surfaces are simulations, not analyzers.
4. **Parallel legacy coupling exists.** `controller_integrated.py` loads all
   seven GUI modules, averages their mutable values, and submits the average
   as the legacy kernel's ego value. This does not alter ProposalGate and
   does not execute an action, but it is a separately reachable decision-like
   runtime result. It contradicts an unqualified statement that only the
   three active regulators can affect any ETHOS decision output.
5. The active `main_app.py` is different: it presents stored Greed/Pride/Envy
   evidence and a read-only controller snapshot, labels the four remaining
   regulators `NOT WIRED`, and does not launch the legacy aggregate.

## 5. Existing frozen/locked boundaries

| Component | Checkpoint / protection | Verification evidence |
| --- | --- | --- |
| Sloth V1 shadow calibration | `ETHOS_SLOTH_V1_SHADOW_CALIBRATION_LOCKED_CHECKPOINT.md`; evaluator V1, threshold 2, enforcement NONE, no ProposalGate change | Current source still uses the separate shadow/calibration path; unittest discovery passes its Sloth suites. |
| Structural Evidence V1.1 | Task 12/14 documents and frozen hashes | `ethos_structural_evidence.py` = `6507e4…bb2b3`; `test_ethos_structural_evidence.py` = `5ea432…857e1f8a9`, matching documented values. |
| Structural Evidence V1.2 | Separate successor, V1.1 remains byte-for-byte isolated | V1.2 has separate implementation/test files; 609-test discovery includes its tests. |
| Wrath research corpus/fixture boundary | Wrath task audits/designs freeze text/corpus inputs and prohibit gate integration | Research-only test suites pass; no production gate import found. |
| Production Gate G/P/E | Architecture and integration readiness audit define bootstrap then Greed/Pride/Envy precedence | Current `ethos_proposal_gate.py` imports only those analyzers; tests pass under unittest. |

There is no Git history, commit, tag, or source-backup convention available
for provenance. These statements rely on present source, documented hashes,
test evidence, and stored artifacts only.

## 6. Calibration-record integrity

The checkpoint's canonical accounting is one `REAL_RUNTIME` observation, one
review, and zero unreviewed records. The raw append-only observation stream
contains **two** records with `provenance: REAL_RUNTIME` for the same
assignment/decision history; the second is the checkpoint's documented
accidental retry. The general calibration summary currently reports total
observations `2`, reviewed `1` and does not itself apply the checkpoint's
canonical exclusion. No additional observation was created by this audit.

This is not evidence of two independent natural observations and must not be
used to advance calibration. It is, however, a freeze-integrity gap: the
machine-readable summary and the locked canonical count disagree unless a
reader also applies the prose checkpoint.

## 7. Known warnings

- The non-failing Wrath fixture `ResourceWarning` described above.
- Global pytest plugin autoload is unusable in this environment because of the
  installed Dash/Plotly metadata failure.
- Pytest is incompatible with two unittest-style `setup(directory)` helpers;
  standard-library unittest discovery is the passing runner found here.
- The retained legacy GUI/radar writes to the runtime SQLite database when its
  operator button is used; it is not the active read-only desktop shell.

## 8. Freeze blockers

1. **Authoritative regression baseline is not reproducibly defined** — the
   checkpoint says 428 tests, current compatible discovery passes 609, and no
   project runner configuration identifies which command/count is canonical.
2. **Legacy aggregate runtime path is outside the proposed freeze boundary** —
   it lets all seven mutable GUI values feed a separate `allowed` result. The
   project must explicitly retire/isolate it or define and test it as a
   non-authoritative legacy diagnostic before claiming an entire-system freeze.
3. **Sloth canonical-count accounting is not mechanically represented** — raw
   `REAL_RUNTIME` summary is 2 while the locked canonical progress is 1. The
   accidental retry needs an immutable machine-readable exclusion/identity
   rule or a clearly authoritative canonical-summary mechanism; do not delete
   or rewrite the locked artifacts to achieve this.

## 9. Deferred research (not V1 blockers once the boundary is explicit)

- Wrath: approved production input/policy/numeric/gate contract.
- Lust: operational definition, vocabulary, fixtures, calibration, policy.
- Gluttony: source-attributed capacity/need/ownership/authorization context
  and Greed collision rule.
- Broader enforcement ladder, executor mediation, lockout, quarantine, model
  disconnect, and distributed/multi-agent control.

## 10. Calibration-dependent work (not a promotion request)

- Sloth requires natural, human-reviewed `REAL_RUNTIME` histories toward the
  stated 30-case engineering target. No smoke/fixture evidence may substitute
  for it.
- Any Sloth promotion review remains separately authorized and must consider
  disagreements, evidence quality, bases, threshold distribution, and safety.

## 11. Nice-to-have work

- Reconcile stale high-level documents that still describe an earlier Sloth
  state or an incomplete test inventory.
- UI polish, richer history/analytics, refactors, and broader GUI integration.
- Repair the non-failing Wrath fixture file-handle warning in a separately
  authorized maintenance change.

## 12. Recommended V1 freeze boundary and exact next action

Once the three blockers are closed, freeze only the **active proposal-only
boundary**: `EthosProposalGate`, its bootstrap policy, Greed/Pride/Envy
analyzers and evidence view, JSONL decision evidence, bounded history/scar
metadata, and read-only controller/desktop projections. Explicitly exclude
Sloth calibration, all research modules, legacy GUI/radar/kernel surfaces,
unintegrated action endpoints, and executors (none exists).

**Exact next action:** authorize a narrowly scoped freeze-integrity remediation
that declares one canonical unittest command/count, makes the legacy
radar/kernel non-authoritative or isolates it from the freeze surface, and
adds a non-mutating canonical exclusion for the documented duplicate Sloth
observation; then rerun this audit without redesigning any regulator.

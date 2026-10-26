# ETHOS V1 Freeze-Integrity Remediation

Date: 2026-10-05. This remediation changed verification definition, legacy-radar isolation, and Sloth canonical-count representation only.

## Conclusion

**ETHOS V1 FREEZE READINESS: READY.** All three freeze-integrity blockers are resolved. ProposalGate semantics, Greed/Pride/Envy behavior, Sloth threshold, and Sloth enforcement did not change.

## Original blockers and resolution

| Blocker | Result | Evidence |
| --- | --- | --- |
| Undefined regression command/count | **RESOLVED** | `ETHOS_V1_VERIFICATION.md` defines one active-root unittest command. |
| Legacy radar/kernel authorization output | **RESOLVED** | The retained radar is visualization-only and explicitly non-authoritative. |
| Sloth raw/canonical mismatch | **RESOLVED** | An append-only canonicalization record excludes the documented duplicate. |

## Canonical regression baseline

The active project root is `linked/main`. Run exactly:

```text
python3 -m unittest discover -v
```

It discovers every `test*.py` module in the active root. Workspace archives, duplicate quarantines, legacy projects, and `.venv` are outside that root; no active test module is excluded.

Final canonical verification: **614 tests passed in 1740.945s**. The count rose from the audit's 609 because this remediation adds two Sloth canonicalization tests and three legacy-radar isolation tests.

### 428 versus the canonical count

The locked checkpoint's 428 result omitted its command, discovery root, and dynamic-test accounting. Current source has 62 unique active test modules and dynamically generated runtime/Sloth unittest methods; no duplicate active test filename was found. All inspected current Sloth operational tests predate the checkpoint, but no Git history or runner configuration exists to recreate the historical subset. The concrete cause is an unreproducible historic verification definition, not duplicate current discovery. The command above and its emitted count are now authoritative.

Pytest is not canonical: global plugin autoload is environment-dependent, and pytest treats two unittest helper functions named `setup(directory)` as hooks.

## Legacy radar/kernel isolation

`controller_integrated.py` was the only active legacy radar implementation. The active `main_app.py` does not import it; archival copies in `duplicates/` and `linked/duplicates/` are not active callers. No ProposalGate code imports or calls the radar.

The radar still opens retained GUI windows, reads values, draws a radar, and shows an aggregate. Its button is now `LEGACY VISUALIZATION SUMMARY`, and its output states `NON-AUTHORITATIVE LEGACY VISUALIZATION`. It no longer imports the runtime kernel, calls `verify_request`, returns an `allowed`/deny result, or writes an enforcement event.

ProposalGate remains the sole authoritative production decision boundary: bootstrap policy, then Greed, Pride, and Envy. It is still proposal-only and has no executor. Sloth cannot affect a ProposalGate result.

## Sloth canonical observation mechanics

Raw entries in `evidence/sloth_shadow_observations.jsonl` were not changed. The append-only companion record `evidence/sloth_shadow_canonicalization.jsonl` identifies `observation-a882f365-5417-4315-a17a-61650f29a2ba` as `EXCLUDED_DUPLICATE` of `observation-bef21470-56cf-45b3-822c-521a877bb42b`.

Validation requires both records to be `REAL_RUNTIME` and share the same assignment and decision-history identity. It does not change raw evidence, create a review, or make an enforcement decision.

`python3 ethos_sloth_shadow_calibration.py summary` now reports:

```text
RAW REAL_RUNTIME = 2
CANONICAL REAL_RUNTIME = 1
REVIEWED CANONICAL REAL_RUNTIME = 1
UNREVIEWED CANONICAL REAL_RUNTIME = 0
```

Sloth remains `SLOTH_RESEARCH_EVALUATOR_V1`, threshold **2**, enforcement **NONE**.

## Files changed

- `controller_integrated.py`
- `ethos_sloth_shadow_calibration.py`
- `evidence/sloth_shadow_canonicalization.jsonl`
- `test_ethos_sloth_shadow_calibration.py`
- `test_legacy_radar_isolation.py`
- `ETHOS_V1_VERIFICATION.md`
- `ETHOS_ARCHITECTURE.md`
- `ETHOS_FILE_MAP.md`
- `ETHOS_V1_SYSTEM_FREEZE_READINESS_AUDIT.md` (supersession note only)
- `ETHOS_SLOTH_REAL_OBSERVATION_RUN_V1.md` (supersession note only)

## Tests and verification

Added coverage proves that duplicate canonicalization preserves raw records and yields the required counts; non-duplicate histories are rejected; the legacy visualization is non-authoritative; changing Sloth affects only that visualization; and the radar has no runtime authorization/event path.

Focused verification passed: **175 tests** across ProposalGate, Greed, Pride, Envy, Wrath research, Sloth shadow/calibration, and legacy isolation. Full canonical verification passed: **614 tests**.

## Remaining warnings

- The known non-failing `ResourceWarning` in `test_wrath_structural_fixture_research.py` remains unchanged.
- Pytest remains non-canonical for the documented environment reasons.

Neither warning blocks the V1 baseline. The canonical standard-library run is green and neither warning changes production behavior.

## V1 freeze boundary

The V1 baseline covers the active proposal-only boundary: ProposalGate, bootstrap policy, Greed/Pride/Envy analyzers and evidence view, JSONL decision evidence, bounded history/scar metadata, and read-only controller/desktop projections. It excludes Sloth calibration, research modules, legacy visualization, unintegrated action endpoints, and executors (none exists).

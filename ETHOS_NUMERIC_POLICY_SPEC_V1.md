# ETHOS Numeric Policy Specification V1

## Status

Research-only specification. `NUMERIC_POLICY_V1_RESEARCH_ONLY` identifies a future review framework; it does not replace current analyzer, gate, or evidence versions.

## Objectives

| Layer | Objective |
| --- | --- |
| Measurement | Deterministically observe proposal-visible cues with existing context and provenance controls. |
| Decision | Calibrate BLOCK decisions to reduce severe false negatives while controlling benign false positives, preserving reproducibility and interpretability. |
| Consequence | Classify repeated central BLOCKs separately from measurement and decision calibration. |

Candidate goals are not optimized: deterministic replay, no hidden semantic inference, regulator-specific review, reversible changes, and explicit human approval.

## Research labels

`BENIGN_ALLOW`, `CONCERNING_ALLOW`, `SHOULD_BLOCK`, `AMBIGUOUS`, `CONTEXT_CONTROL`, `PROVENANCE_CONTROL`, `PARAPHRASE_PAIR`, `BOUNDARY_CASE`, and `UNRESOLVED` are annotations only. Each case must retain exact proposal fields, provenance/source, rationale, confidence, reviewer, current score/tolerance/result, and mismatch status. Only strong `BENIGN_ALLOW`/`SHOULD_BLOCK` examples enter descriptive confusion metrics; all other labels remain visible but excluded.

## Cost model

Future calibration distinguishes true/false positives and negatives. Relative costs are **UNSET**: available project evidence does not justify them, and regulators may require different assumptions. No runtime cost values are defined here.

## Validity rules

1. Never tune from one anecdote.
2. Separate calibration from held-out review once the corpus is sufficiently large.
3. Do not change vocabulary with thresholds in one experiment.
4. Hold context/provenance semantics fixed during threshold study.
5. Identify every changed historical case and add regressions for any production change.
6. Do not silently make ambiguous labels ground truth.
7. Require regulator-specific evidence for regulator-specific changes.
8. Require explicit human review and preserve the prior policy for replay comparison.

## Hypothetical evaluator contract

The evaluator reads already-recorded scores. It may compare candidate tolerances, `>` versus `>=`, regulator-specific tolerances, and Greed-only weights. It never alters analyzer configuration, gate configuration, evidence/history/scars, or current policy. It does not search or optimize candidates.

## Versioning requirement

Any future production numeric-policy version (for example `NUMERIC_POLICY_V2`) must identify measurement version, numeric-policy version, and gate version in replayable evidence. Runtime migration is explicitly deferred.

## Preconditions for future tuning

Reviewed objective and owner; labeled benchmark corpus; false-positive/false-negative tradeoffs; decision costs; calibration method; held-out review; changed-case report; regression tests; independent signoff.

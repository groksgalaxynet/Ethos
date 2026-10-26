# ETHOS Policy Rationale Audit V1

## Scope and conclusion

This is a read-only provenance audit. It does not change scoring, enforcement, or consequences.

**Conclusion:** the current 70 defaults are **historically inherited** from GUI slider defaults and documented bootstrap continuity. The strict `>` operator and cue-magnitude semantics are **currently unjustified** by available project evidence. No reviewed calibration, decision-cost analysis, or policy-owner approval was found.

## Policy provenance table

| Parameter | Current value | Historical source | Explicit rationale? | Classification |
| --- | ---: | --- | --- | --- |
| Greed vector tolerance | 70 | Current/legacy GUI slider default 70 / 0.7 | No | HISTORICAL_DEFAULT |
| Pride/Envy vector tolerance; all overall tolerances | 70 | Current/legacy GUI slider default 70 / 0.7 | No | HISTORICAL_DEFAULT |
| Violation operator | `score > tolerance` | Current implementation; legacy labels display `Lock ≥ N` but do not enforce | No | UNJUSTIFIED_CURRENT_POLICY |
| Default weights | 1.0 | Equal-initialized GUI weighted-preview controls | No | IMPLEMENTATION_DEFAULT |
| Cue magnitudes / 100 cap | 30–80, capped at 100 | No individual provenance found | No | UNJUSTIFIED_CURRENT_POLICY |

## Observed facts

- `ETHOS_ARCHITECTURE.md` states that equal weights and tolerance 70 deliberately mirror GUI defaults “for continuity only” and are bootstrap defaults, not validated policy.
- `ETHOS_CONTEXT.md` and `ETHOS_MISSING_REGULATOR_CONTRACTS.md` identify the GUI 70 as a historical simulator default, not an adopted threshold.
- Current and legacy GUI sliders display `Lock ≥ 70` / use `0.7`, but their values are simulated or display-only and are not an enforcement rationale.
- The analyzers use strict `>` for vector and overall violations. **Current operator rationale not established.**
- No evidence establishes that vector meanings have equivalent severity, that their scores are comparable, or that equal Greed averaging has a reviewed decision-policy meaning.
- No calibration evidence establishes that 30, 55, 70, 75, 80, or 100 correspond to probability, risk, severity, or data-derived categories. They are current deterministic heuristic constants; 100 is arithmetic saturation in implementation.

## Boundary Characterization linkage

Boundary Characterization V1 is empirical behavior evidence only:

- Pride and Envy single variants score exactly 70 and ALLOW under `>`.
- Greed DPI `capture accounts` and OO `replicate indefinitely` score exactly 70 and ALLOW absent another policy.
- A mechanically reachable Greed overall 70 can still BLOCK through independent vector violations.
- Individual-vector 69 and 71 are unreachable in the current discrete vocabulary.
- Same-vector combinations can exceed 70; several Greed dimensions cannot individually block; paraphrase sensitivity and context/provenance controls are measurement-contract findings.

These facts expose decision-policy questions; they do not identify the correct threshold or establish sentence-level semantic truth.

## Separation of concerns

| Layer | Current evidence | Audit conclusion |
| --- | --- | --- |
| Measurement contract | Exact cues, contextual suppression, source provenance, arithmetic/caps | Deterministically specified, but cue magnitudes lack documented calibration semantics. |
| Decision policy | `> 70`, equal-weight Greed overall, regulator policy IDs | Numeric rationale not established. |
| Consequence policy | History after BLOCK; bounded warning/minor/major scar states | Separate from measurement and threshold rationale; not evaluated as a reason to retain 70. |

## Requirements before any future tuning

1. Reviewed policy objective and named policy owner.
2. Regulator-specific harm/false-positive/false-negative tradeoffs.
3. Labeled, reproducible benchmark corpus with context and provenance controls.
4. Explicit decision-cost assumptions and intended role of individual versus overall vectors.
5. Calibration procedure for cue magnitudes and any score aggregation.
6. Independent review/signoff and regression criteria before adoption.

No threshold number is proposed by this audit.

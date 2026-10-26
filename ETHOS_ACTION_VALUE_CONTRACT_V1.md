# ETHOS++ Action Value Contract V1

## Scope

`ActionBenefitClaim` and `ActionEffortClaim` are research-only, neutral, source-attributed measurements. They establish objective-relative comparison facts only. They do not label an action good, easy, lazy, wasteful, ethical, or Slothful.

## Claim fields

Each claim contains claim ID, objective ID, action ID, actor ID, scope ID, value, measurement-basis ID, phase, validity interval, producer ID, source attribution, and optional authority ID. Attribution supplies source, source instance, scope, availability time, verification state, and evidence reference.

`EXPECTED` is decision-time estimate evidence. `OBSERVED` is post-action measurement evidence. They are distinct and never compared as if interchangeable. A future Sloth consumer generally needs expected benefit and effort valid at the decision time.

## Measurement basis, units, and ordinal scales

`MeasurementBasis` names one dimension (`BENEFIT` or `EFFORT`), one representation (`NUMERIC` or `ORDINAL`), and one unit/scale. Numeric values compare only under the same basis. Ordinal values compare only when that basis provides an explicit ordered scale, such as `LOW < MEDIUM < HIGH`.

No conversion is implied: tokens, joules, seconds, API calls, utility scales, and arbitrary labels are not comparable across bases. Multi-dimensional effort remains `NOT_COMPARABLE` unless a separately authorized aggregation basis is supplied by an authority; this contract supplies no weights.

## Authority and conflict

`MeasurementAuthorityClaim` separately identifies the producer, measurement basis, disposition, and attribution. Only matching `CONFIRMED` authority makes a claim usable. Agent self-estimates are permitted only as explicitly attributed claims; they do not become authoritative absent a matching authority claim.

Different usable values for the same action, objective, basis, and decision context yield `CONFLICT`; the model never averages. Missing values yield `UNKNOWN`. Missing authority, incompatible objective/scope/basis/phase/unit, invalid ordering, or invalid time yields `NOT_COMPARABLE`.

## Temporal validity and history linkage

A claim is usable only when `valid_from <= decision time <= valid_until` (when an end exists). Later or expired estimates cannot rewrite historical decision context.

Claims attach by exact objective/action IDs to `ActionDecisionRecord` candidates, then are evaluated at `DecisionHistoryEntry.decided_at`. The history preserves the existing explicit benefit/effort/resource fields but does not reinterpret them; typed claims provide the comparison semantics.

## Outputs and non-goals

Comparison returns `A_GREATER`, `B_GREATER`, `EQUAL`, `UNKNOWN`, `CONFLICT`, or `NOT_COMPARABLE`. It proves only a measurement relation. There is no ProposalGate import, production regulator change, frozen Structural Evidence change, universal utility scale, hidden reasoning source, automatic normalization, or Sloth evaluator.

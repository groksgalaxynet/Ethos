# ETHOS++ Sloth Research Evaluator V1

## Status

**RESEARCH ONLY.** `evaluate_sloth_research()` consumes validated factual decision contexts. It is not imported by ProposalGate, controller, or production regulators.

## Authorized V1 rule

For one coherent assignment/work history, a decision qualifies only when its composite context proves: authoritative active `REQUIRED` assignment; required action available; no blocker/prerequisite/exclusion; another action selected; required action has greater `EXPECTED` objective benefit; and selected action has lower `EXPECTED` effort. A result is `POSITIVE` only when the qualifying count meets the explicit policy threshold.

The default `SlothEvaluationPolicy.minimum_repeated_avoidance_count` is **2**. This research default implements the literal minimum meaning of repeated; it is configurable and not a universal moral constant. Result evidence includes threshold, qualifying count/IDs, required-action selection count, excluded/unknown/conflict/non-comparable IDs, references, and deterministic reason code.

## States and counterexamples

`POSITIVE` means the configured research rule found repeated qualifying avoidance behavior in supplied factual evidence. `NEGATIVE` means sufficient complete evidence exists but the threshold/pattern is not met. `INSUFFICIENT_EVIDENCE`, `CONFLICT`, `NOT_COMPARABLE`, and `EXCLUDED` retain their upstream meanings and never become negative or qualifying evidence.

One occurrence is `NEGATIVE` at threshold 2. Prerequisite, blocker, delegation-away, cancellation, supersession, completion, and expiration are excluded. Equal/higher-benefit alternatives or alternatives not lower effort do not qualify. Later required-action selection does not erase earlier qualifying events, but is exposed in the result; the evaluator never claims perpetual avoidance.

## Coherent histories and non-goals

Evaluation accepts one assignment/work identity at a time. It does not combine skips of different obligations, objectives, actors, scopes, or duplicate decision IDs to reach a threshold. Ordered history validation remains authoritative.

The evaluator matches the owner definition only as a bounded observable rule: repeatedly selecting a lower-effort, lower-benefit alternative while a higher-benefit required action is active, available, and unblocked. It does not prove internal laziness, motive, desire, consciousness, hidden reasoning, or any production policy violation.

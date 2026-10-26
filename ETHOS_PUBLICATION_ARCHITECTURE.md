# ETHOS++ Publication Architecture

This document describes the published boundary without rewriting the frozen
historical V1 documents. It distinguishes operational authority from research
observation.

## V1: the only production decision path

```text
ActionProposal
  -> EthosProposalGate.inspect
  -> bootstrap checks
  -> GreedAnalyzer / PrideAnalyzer / EnvyAnalyzer
  -> ALLOW or BLOCK
  -> evidence, bounded violation history, optional consequence metadata
  -> stop
```

`ethos_proposal_gate.py` is the sole V1 production authority. It imports only
the three production analyzers for its regulator decision. An `ALLOW` is an
approval record, not execution. No V1 source in this publication grants an
approved proposal an executor, tool authority, lockout, quarantine, or model
disconnect capability.

Sloth remains a frozen, separate shadow/calibration subsystem. Historical
legacy GUI/radar/kernel modules are retained as baseline material but are not
an alternative ProposalGate authority and must not be described as production
enforcement.

## V2: non-enforcing shadow research

```text
RuntimeShadowEvent
  -> default-disabled per-regulator configuration
  -> existing V2 evaluator
  -> V2Classification (enforcement=NONE)
  -> append-only result record
  -> append-only observation record
  -> optional, separate human-review record
```

The V2 entry points are:

- `ethos_generic_shadow_config.py`
- `ethos_generic_shadow_observation.py`
- `ethos_runtime_shadow_runner.py`
- `ethos_runtime_action_receipt_observer.py`
- `ethos_local_tool_execution_receipts.py`
- `ethos_dual_action_provenance.py`

V2 evaluation delegates to the existing research adapters and classifiers:

- Wrath: `wrath_harmful_action_research.py` and its factual-context inputs.
- Gluttony: `gluttony_resource_research.py`,
  `gluttony_runtime_evidence_bridge.py`, and resource-metering inputs.
- Lust contextual: `lust_incentive_research.py`.
- Lust categorical: `lust_categorical_policy_research.py`.

`ethos_remaining_regulators_v2.py` preserves V2 classification semantics. A
runner event may be malformed or incomplete; it is rejected or classified as
insufficient evidence rather than completed with invented facts.

## Local receipt boundary

The receipt boundary is isolated from V1:

```text
model response
  -> schema validation
  -> independently supplied authorization reference
  -> isolated, allowlisted local action or denial
  -> append-only execution outcome / receipt
  -> receipt observer
  -> V2 shadow runner if the regulator is explicitly enabled
```

The model cannot authorize itself. A denied request remains `NOT_EXECUTED`; no
receipt is fabricated. The demonstrated file operation was constrained to a
disposable local target. V2 code provides no path to `EthosProposalGate`,
production regulator enforcement, Scar/consequence services, or frozen Sloth
modules.

## Provenance and evidence limits

Supported provenance labels distinguish `REAL_RUNTIME`, `SYNTHETIC_FIXTURE`,
and `REPLAY`. A local request or transport event is not equivalent to an
independently observed world fact. Simulated environmental facts remain
simulated. Duplicate identities are preserved in raw append-only streams and
can be excluded from calibration counts through separate canonicalization
records.

The checked-in Phase 5 fixtures are synthetic and versioned. Runtime JSONL
streams, local telemetry, authorizations, receipts, target files, databases,
and live-model outputs are excluded from publication.

## Supported verification boundary

The publication supports syntax/import checking and the focused V2 tests
listed in the README. The Phase 5G and 5H reports record their own narrow test
results. This does not constitute a full historical V1 regression, independent
replication, real-world calibration, or production authorization.

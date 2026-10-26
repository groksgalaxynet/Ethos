# ETHOS Controller Contract V1

## Status and authority

ETHOS_CONTROLLER_CONTRACT_V1 is an immutable, non-authoritative observation projection. EthosProposalGate remains the sole current authority for ALLOW/BLOCK. The controller cannot override a decision, rerun analyzers, write evidence/history/scars, execute actions, call tools, generate proposals, or invoke an LLM.

The controller aggregates structure and already-recorded evidence only. It does not calculate a total ETHOS score, average, maximum, weighted cross-regulator score, moral score, safety probability, or risk probability.

## Input and reconstruction

The supported flow is proposal -> EthosProposalGate.inspect() -> GateDecision/evidence -> ControllerSnapshot.from_gate_result(...). ControllerSnapshot.from_evidence_record(...) reconstructs the supported observation shape from a persisted JSONL gate record without reading or modifying history independently.

Stored proposal, decision, policy IDs, regulator evidence, and stored consequence metadata are reconstructable. A separate unseen history row, external scar payload, and future temporal information are unavailable and never invented.

## Snapshot contract

- Proposal state contains the exact stored proposal or NOT_AVAILABLE.
- Regulator state contains complete Greed, Pride, and Envy evidence exactly as produced.
- Gate state contains the decision, policy IDs, first authoritative policy and policy family, and an ETHOS_PROPOSAL_GATE authority marker.
- History/consequence state exposes only already-stored occurrence, identity, state, and scar metadata, marked read-only.
- Temporal state is UNSUPPORTED. Reserved fields are episode_id, step_index, goal_id, prior proposal references, action outcome references, and trajectory evidence.

Lust, Sloth, Wrath, and Gluttony appear explicitly as UNSUPPORTED; no score or inferred state is created for them.

## Primary and secondary violations

The primary violation is present only when the gate's first authoritative policy is a regulator policy. It mirrors current gate ordering: Greed, then Pride, then Envy after bootstrap checks. Additional independently observed regulator violations remain secondary. A bootstrap primary remains distinguishable from regulator violations.

The benchmark Pride/Envy exact-70 cases remain faithfully ALLOW: both regulators can be OBSERVED/non-violating with zero violations. The controller does not change them.

## GUI

The existing main_app.py shell provides a read-only Controller Observation tab. It reads the latest stored evidence and displays controller version, gate decision/policy, individual regulator status, primary/secondary violations, history/consequence availability, unsupported regulators, and temporal UNSUPPORTED. It has no action controls and does not open the gate or analyzers.

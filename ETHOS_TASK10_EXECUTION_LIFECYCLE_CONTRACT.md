# ETHOS++ — Task 10

## Neutral Proposal → Execution → Observation Lifecycle Contract

Status: design and architecture audit only. No implementation is authorized.

## Actual current boundary

Proposals enter through saved CLI JSON, the Ollama adapter, direct mappings, and tests. EthosProposalGate.inspect analyzes a proposal, returns ALLOW or BLOCK, and writes a gate evidence record. It never executes a proposal. The CLI only requests/proposes and inspects. EthosController only projects existing gate records. History/scar persistence stores gate consequences, not action results.

There is no action runner, tool callback, execution return channel, target-state probe, post-action report, or lifecycle verifier connected to the gate. EthosRuntime.log_event is generic logging and does not establish an action occurred. artifact_observer is a real read-only local-artifact hash observer, but has no proposal/action link. Factual-context and producer-conformance modules are research-only submitted-fact models, not active lifecycle producers.

ALLOW means only that the present gate admitted a proposal under current policy. BLOCK means only that it did not. Neither proves, suppresses, predicts, or records execution.

## Independent stages

| Stage | Identity | Minimum meaning |
| --- | --- | --- |
| Proposal | existing proposal_id | Caller declaration of intended action and optional targets. |
| Execution | execution_id | Source-attributed occurrence or state claim. |
| Observation | observation_id | Observer-attributed neutral fact about entity or event. |
| Verification | verification_id | Fact-specific verification of one identified assertion. |

The four are never aliases. A proposal has zero or many executions. An execution may have no observation. An observation does not prove an intended outcome. Verification establishes no universal authority.

## Identity, scope, and provenance

Proposal identity remains (agent_id, session_id, proposal_id). A future execution_id is caller/runtime supplied, nonempty, stable in an explicit execution scope, and distinct from proposal_id. Do not generate it from time, random values, or text.

Execution identity: (execution_scope, execution_id). A record additionally retains source, source instance, assertion ID, scope, availability time, and lineage only when actually derived. An originating proposal reference is the separately supplied proposal scope and proposal_id. Exact replay is idempotent; a divergent record sharing an identity is a collision.

The execution actor is explicit or UNKNOWN, not copied from the proposer. It may be one or many participants, a tool/runtime entity, or UNKNOWN. Executed targets are separately declared zero-or-many targets; they may match, omit, differ from, or be UNKNOWN relative to proposal targets. Mismatch is retained without reconciliation.

## Execution state and outcome

No current runtime supplies execution-status semantics. Task 10 therefore does not authorize a new status enum. A future adapter may map only explicit source reports to existing V1.1 event state values: PENDING, ACTIVE, COMPLETED, INCOMPLETE, or UNKNOWN. Gate ALLOW/BLOCK must never map to execution state.

Completion is an occurrence/state claim, not an outcome claim. Existing V1.1 outcomes (SUCCEEDED, FAILED, INCOMPLETE, UNKNOWN) may represent only a separately explicit source claim. A tool return does not establish that a target changed as intended. Target change should be a later OBSERVED assertion about target state or a separately verified fact.

## Observation and verification

An observation is an OBSERVED assertion with unique observation/assertion ID, explicit observer, observed entity/event, source instance, scope, observation time, and availability time. OBSERVED_BY preserves observer-to-entity structure; HAS_STATE or HAS_OUTCOME carries only supported neutral finite values. Unrecognized values remain opaque/non-consumable.

An executor saying it acted is DECLARED. A sensor reporting a state is OBSERVED. Neither is automatically verified. Verification refers to one assertion and contains verifier, method reference, evidence reference, and verification time. It verifies that fact only and creates no global trust property.

## Relations, time, conflicts, and UNKNOWN

V1.1 already has PARTICIPATES_IN, TARGETS, OBSERVED_BY, HAS_STATE, HAS_OUTCOME, BEFORE, AFTER, verification, lineage, and availability. BEFORE/AFTER records supplied sequence only; it never establishes causation.

V1.1 lacks a neutral typed relation from execution event to originating proposal event. REQUESTED relations do not mean execution, temporal relations do not mean reference, and opaque metadata is not a structural consumable link. Therefore the adequacy decision is: V1.1 EXTENSION MAY BE REQUIRED. A narrowly reviewed future EXECUTION_OF(execution, proposal) relation would be the correct structural solution; until then a proposal reference is opaque provenance only.

Keep proposal time, gate decision time, execution start/end, observation time, verification time, and availability time separate. Missing time is UNKNOWN; insertion order is not evidence.

Conflicting reports remain attributed, scoped assertions. The shared layer selects no winner. UNKNOWN is first-class for occurrence, actor, target, state, outcome, verifier, and order. Missing execution evidence does not mean non-execution.

## Multi-execution, swarm, and gate behavior

One proposal may have zero or many executions, including retry, partial work, delegation, and repeated calls. No one-to-one cardinality is permitted. In a swarm, proposer, router/controller, executor, observer, and verifier remain distinct entities and roles. No blame, policy authority, or ethical conclusion follows.

A blocked proposal normally has no execution record. If another system later acts, it must provide independent execution evidence. Gate state and missing records resolve nothing about occurrence.

## Security review

Forged or spoofed actor, executor, observer, and verifier identities remain claims, not authentication. Duplicate IDs are exact replay only when canonical content matches; divergent records collide. Missing/cross-session proposal references remain unresolved or quarantined, never rebound. Target mismatch, false status, conflicting outcome, future-evidence leakage, replayed observation, and lineage echo remain source- and time-attributed facts. Verification never upgrades a source into global authority.

The shared lifecycle layer excludes policy, ethical, harm, coercion, retaliation, proportionality, and regulator-specific vocabulary. It does not reinterpret ALLOW/BLOCK.

## First implementation slice

No real runtime produces execution facts today. The first experiment should be test-only:

explicit caller-supplied execution record
→ strict identity/scope/provenance validation
→ neutral V1.1 execution event plus actor/target assertions
→ no regulator consumer

It must preserve UNKNOWN and an optional opaque originating-proposal reference pending typed relation review. It must not create execution from a gate decision and must emit no observations, outcomes, or verification. A later separate experiment could accept caller-supplied observation; automated observation is not justified.

## Task 4 and cross-regulator relevance

| Case | Potential lifecycle result |
| --- | --- |
| H01 | Still requires observation. |
| H07 | Partially unlocked; still requires observation and fact-specific verification. |
| E06 | Partially unlocked; still requires ordering. |
| E01 | Still requires ordering and independent execution records. |
| F01 | Still requires measurement and comparison basis. |

Lifecycle evidence may eventually provide bounded inputs to Greed, Pride, Envy, Sloth, Wrath, and future consumers. Each consumer must separately decide source, fact class, scope, time, and verification usability. No current regulator may consume it.

## Actual candidate producers

No qualifying execution producer exists today.

- EthosRuntime.log_event is generic runtime logging and is insufficiently typed.
- artifact_observer is a real read-only artifact observer, not action-linked.
- Research factual-context records can model submitted execution-result context but are not runtime producers.
- The recommended first producer is the isolated test-only caller-supplied execution-record adapter.

## Decision

EXECUTION LIFECYCLE CONTRACT READY FOR ISOLATED IMPLEMENTATION


# ETHOS++ Sloth Producer Readiness Audit

## Verdict

**RESEARCH_ONLY.** The validated evaluator can classify supplied evidence, but the current runtime cannot produce the mandatory evidence chain from real agent behavior. Existing schemas and test fixtures are not producers.

## Dependency graph

```text
SlothEvaluationResult
  <- DecisionContextHistorySummary
    <- DecisionContextEvidence
      <- ordered DecisionHistoryEntry + ActionDecisionRecord
      <- RequiredWorkAssignment + AuthorityClaim + LifecycleClaim
      <- expected ActionBenefitClaim + ActionEffortClaim + measurement authority
      <- candidate availability + blocker/prerequisite facts
```

The only current production path is `ActionProposal -> EthosProposalGate -> JSONL GateDecision`. It records one caller/model-declared proposal, gate analysis, timestamp, agent/session identity, and an `execution = NOT_EXECUTED_TASK_1` marker. It does not emit an objective assignment, candidate set, selection event, execution event, action-value claim, lifecycle claim, or ordered decision history.

## Producer readiness matrix

| Evidence needed | Contract | Current producer | Status | Source-attributed? | Independently verifiable? | Agent can self-certify? | Persisted? | Ready? | Exact gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Objective/work assignment, assignee, REQUIRED state | RequiredWorkAssignment | None; `ActionProposal.task` is free text | MISSING | No | No | Yes, if caller/model supplies prose | Proposal only | No | Authority-aware assignment producer and lifecycle store. |
| Assignment authority | AuthorityClaim | Existing research factual-context conformance model only | RESEARCH_ONLY | Schema only | No runtime resolver | Yes | No | No | Fact-specific authority resolver for assignment sources. |
| Assignment lifecycle | AssignmentLifecycleClaim | None | MISSING | No | No | N/A | No | No | Immutable active/cancelled/superseded/delegated/completed event producer. |
| Candidate actions before choice | ActionDecisionRecord candidates | None; boundary demo has illustrative candidates only | MISSING | No | No | Agent could fabricate | No | No | Planner/scheduler candidate producer before selection. |
| Selected action | ActionDecisionRecord selected action | Proposal declares intended action only | REAL_RUNTIME_BUT_UNTRUSTED | Agent/session/timestamp exist | No independent choice observer | Yes | Gate JSONL | No | Selection event from planner/runtime, distinct from proposal. |
| Execution/completion/outcome | V1.2 execution and factual-context completion | Test-only caller-supplied execution producer; generic runtime log | TEST_FIXTURE_ONLY | Caller attribution only | No | Yes | Generic runtime event possible | No | Runtime execution/outcome observer; gate has no executor. |
| Expected objective benefit | ActionBenefitClaim | None | MISSING | No | No | Yes | No | No | Objective-relative estimator/scheduler basis with authority. |
| Expected effort | ActionEffortClaim | None | MISSING | No | No | Yes | No | No | Basis-aware estimator for time/tokens/calls/etc. |
| Measurement authority | MeasurementAuthorityClaim | None | MISSING | No | No | Yes | No | No | Basis-specific authority mapping; self-estimates cannot self-confirm. |
| Availability | candidate `AVAILABLE` | None | MISSING | No | No | Yes | No | No | Scheduler/environment/tool availability producer at decision time. |
| Blocker/prerequisite | contextual factual claims | Research-only claim fields and lexical Sloth studies | RESEARCH_ONLY | Fixtures have attribution | No runtime source | Yes | No | No | Dependency/permission/resource/environment fact producer. |
| Ordered history | DecisionHistoryEntry | Gate JSONL is append-only proposal history, not decision history | REAL_RUNTIME_BUT_UNTRUSTED | Evidence ID/time/agent/session | Only for gate record | Proposal can self-report | JSONL | No | Decision ID/sequence/objective/scope/candidates/selection recorder. |

## What is real today

`EthosProposalGate` and its JSONL store are real production components. They persist caller/model proposal declarations with agent/session/timestamp and gate result. `EthosRuntime.log_event()` also persists generic agent-tagged JSON payloads to SQLite. Neither establishes a candidate set, selection among alternatives, independent assignment authority, benefit/effort estimate, availability, or execution truth. The CLI/Ollama adapter is a proposal producer, not a choice/execution producer.

The only execution-chain implementation is explicitly test-only and caller-supplied (`ethos_execution_producer_research.py`). Wrath structural producers and existing Sloth corpora are likewise research/test evidence. None may be counted as real coverage.

## Gaming and trust boundaries

The evaluated agent can presently control or self-report task prose, target, arguments, exposed reasoning, raw model output, and any hypothetical caller-provided candidate/benefit/effort/availability data. It can therefore make work appear unavailable, low-benefit, high-effort, optional, or blocked unless an independent source supplies those facts.

Assignment/authority should come from a user, workflow controller, scheduler, or explicit workflow contract. Candidates and selection should come from a planner/runtime boundary. Availability, blockers, prerequisites, and actual cost should come from dependency, permission, tool, environment, and resource monitors. Benefit/expected-effort should come from a basis-authorized scheduler/controller/estimator; agent estimates may be retained only as clearly self-attributed claims. An ordered recorder should be append-only and assign sequence/time independently of the evaluated agent.

## Smallest real producer architecture

1. **Objective-assignment producer:** emits authority-referenced required work and lifecycle events.
2. **Decision recorder:** emits candidates, selected action, actor/objective/scope, decision ID, timestamp, and independent sequence before execution.
3. **Decision-value/availability producer:** emits basis-authorized expected benefit/effort plus availability, blockers, and prerequisites at that decision boundary.

The smallest first implementation is the **Decision recorder** only when paired with caller/controller-supplied objective assignment reference; however it cannot make Sloth operational alone. The smallest complete usable set is all three components above. Their neutral facts are reusable: Wrath can consume selected action/target/environment context; Lust can consume decision/objective/incentive records; Gluttony can consume expected/observed resource-cost and availability records.

## Embodied compatibility

The producer boundaries do not assume software-only actions. A candidate can be a tool call or a move/repair action; effort bases can represent time/tokens or energy/distance; availability can represent API reachability or path/tool/object access. No Blender or robot integration is implied.

## Readiness decision

The current runtime cannot evaluate Sloth against real behavior today. Mandatory positive-rule inputs remain synthetic/test-only or missing, especially candidate alternatives, authoritative assignment, independent expected values, availability context, and ordered selection history.

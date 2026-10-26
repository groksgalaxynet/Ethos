# ETHOS++ Action Evidence Model Audit

## Decision

A source-attributed `ActionDecisionRecord` is justified as the next shared research abstraction. It is broader than an execution record: it represents an objective, candidates, a selection, optional execution/outcome, and explicit neutral context. It contains no ethical label, score, policy, approval, or gate result.

The isolated prototype is `ethos_action_decision_research.py`. It imports no production modules and is not imported by the proposal gate, controller, or existing regulators.

## Existing evidence and gaps

| Neutral fact | Status | Class | Required next source |
| --- | --- | --- | --- |
| Proposal identity and proposed action | Existing `ActionProposal`; V1.2 proposal role possible | A | Existing proposal evidence |
| Objective identity | Task prose only | D | Stable caller/planner objective ID and scope |
| Candidate actions / selected alternative | Absent | D | Source-attributed planner/caller record |
| Execution, outcome, target state | Gate intentionally has none | E | Execution/outcome/observer producer |
| Required/optional work | Absent | D | Assignment/obligation claim |
| Benefit, effort, resource estimate | Absent | D | Explicit estimate with basis/scope |
| Actual resource cost, quota, capacity | Absent | E | Resource-meter/quota producer |
| Target | Text and optional declared target type exist | A/D | Operational identity claim where needed |
| Authorization, consent, instruction | Raw user text only | D | Normalized source-attributed claim |
| Threat/protective context | Absent | D/E | Caller or observer claim |
| Incentive association | Hidden reward unavailable | F/D | Visible metric/contract claim only |
| Time/order/history | Proposal timestamp; V1.1 temporal terms | A/D | Linked decision history |
| Source attribution | Proposal/adapter and V1 assertions exist | A | Source, instance, scope, availability per claim |

No hidden chain-of-thought is an eligible source. Research-only Wrath/Sloth lexical evidence is `B`, but it does not establish these operational facts. No ethical fact is safely Class `C` deterministically derivable.

## Neutral record and shared fields

```text
record identity + objective identity + record source/instance/scope/availability
candidate actions: identity, declared benefit/effort/resource cost,
                   required status, availability
selected action; optional execution state/outcome; repeat count
contextual claim: claim identity, action identity, neutral kind/value, source
```

All four share objective/action identity, selected action, source attribution, availability time, UNKNOWN/conflict retention, and explicit user/objective context. Sloth, Lust, and Gluttony additionally share alternatives and declared benefit. Sloth and Gluttony share effort/resource comparison and history/justification. Wrath and Gluttony share target and authorization context. Wrath and Lust share action relation (proposed/executed/encouraged versus described).

Unique fields are: Sloth—required status, blocker, prerequisite/delegation; Wrath—expected material harm, target type, consent/proportionality/protective context; Lust—visible incentive association and objective conflict; Gluttony—resource type/cost, capacity/ownership/need, resource relation, and objective justification.

## Execution-record conclusion

**B: execution evidence belongs inside the broader neutral model.** Execution alone cannot establish avoided alternatives, harmful context, incentive conflict, or unnecessary resource choice. It can later establish occurrence/state and actual metered cost, without deciding any regulator result. V1.2 can represent structural proposal/execution roles and linkage once such records exist, but does not turn a record into authorization, success, or ethical evidence.

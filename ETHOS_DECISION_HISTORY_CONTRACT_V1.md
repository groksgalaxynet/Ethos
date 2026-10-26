# ETHOS++ Decision History Contract V1

## Scope

This research-only contract proves factual choice history under a required-work assignment. It may establish “A was required and available while the actor selected another action.” It never establishes Sloth, intent, fault, policy meaning, or gate outcome.

## New neutral structures

`DecisionHistoryEntry` wraps the existing `ActionDecisionRecord` with the missing factual fields: actor ID, scope ID, explicit positive sequence ID, decision timestamp, source-instance ID, and optional execution/completion state. This avoids changing the existing action record.

`BindingResult` binds an assignment to one decision. `RepeatedNonSelectionSummary` reports factual counts: valid decisions, required-action availability, required-action selections, other selections, and excluded decisions/reasons.

## Assignment-to-action proof

Binding succeeds only with exact identifier equality: assignment objective equals decision objective; assignment work ID equals a resident candidate action ID; assigned actor equals history actor; assignment scope equals history scope. The assignment must have matching confirmed `ASSIGN_REQUIRED_WORK` authority, `REQUIRED` state, and active lifecycle at the decision timestamp. The candidate must explicitly be `AVAILABLE`.

No text similarity, task label, list position, priority guess, or hidden reasoning may bind an assignment to an action. Result states distinguish `MATCH`, `OBJECTIVE_MISMATCH`, `ACTOR_MISMATCH`, `SCOPE_MISMATCH`, `AUTHORITY_UNCONFIRMED`, `INACTIVE_ASSIGNMENT`, `REQUIRED_ACTION_NOT_AVAILABLE`, `UNKNOWN_AVAILABILITY`, and excluded factual context.

## Ordering and history identity

History records must have unique decision IDs and sequence IDs, one actor, one objective, one scope, and one source instance. Sequence IDs order the records; strictly increasing explicit timestamps corroborate that order. Duplicate IDs, duplicate/invalid sequence, timestamp collision, reversed time, mixed actor/objective/scope/source instance, and malformed time produce an invalid/unknowable history. Array order has no evidentiary meaning.

## Active obligation and exclusions

Lifecycle claims are filtered by their explicit availability time for each decision. Completed, cancelled, superseded, delegated-away, blocked, and expired assignments are inactive and later decisions are excluded. A valid blocker or selected-action prerequisite is an `EXCLUDED_CONTEXT`, not free non-selection. Unknown candidate availability is `UNKNOWN_AVAILABILITY`, not a skipped required action.

## Benefit, effort, execution, and outcome

The existing action record already holds explicit optional benefit, effort, and resource-cost values for candidates. The history preserves them without deriving values from descriptions. Missing values remain unknown.

Selection, execution, completion, and successful outcome stay distinct. Selection proves only decision evidence. An execution producer may later prove an occurrence/state; an outcome/observer producer is needed for completion or target-state claims. Neither is required merely to prove selection.

## Repeated non-selection

The factual summary has no moral threshold. It counts only `MATCH` bindings. It separately records how often the required action was available, selected, or another action was selected, and lists all excluded records with reasons. A future Sloth evaluator would still require explicit benefit/effort comparison and any authorized decision rule.

## Non-goals

No ProposalGate integration, production regulator change, Sloth classifier, frozen Structural Evidence modification, authority-source hard-coding, hidden-reasoning access, or ethical conclusion is introduced.

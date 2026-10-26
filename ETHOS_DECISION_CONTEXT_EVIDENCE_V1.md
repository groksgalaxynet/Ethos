# ETHOS++ Decision Context Evidence V1

## Purpose

`DecisionContextEvidence` is a research-only composite of Required Work, Decision History, and Action Value contracts. It establishes factual alignment for one historical decision; it never emits Sloth, policy, or gate results.

## Joined evidence and exact rules

The composite references existing assignment, assignment authority, lifecycle, decision, candidate, contextual-claim, benefit/effort claim, basis, and measurement-authority IDs. It creates no competing raw schema.

Exact objective, actor, scope, and action IDs must align. Assignment authority must be confirmed; requirement active; required action a resident `AVAILABLE` candidate; and benefit/effort claims `EXPECTED`, basis-compatible, authority-confirmed, and valid at `DecisionHistoryEntry.decided_at`.

## States

`COMPLETE_CONTEXT` means required facts align. `INCOMPLETE_CONTEXT` means a binding or candidate is absent/mismatched. `UNKNOWN` preserves unknown availability, authority, selection, or value. `CONFLICT` preserves lifecycle or measurement disagreement. `NOT_COMPARABLE` preserves incompatible, stale, observed-phase, or unauthorized measurements. `EXCLUDED_CONTEXT` preserves valid blocker, prerequisite, or inactive lifecycle context.

## Factual pattern and history

A complete record exposes required action active/available, required action selected or not, alternative selected or not, blocker/prerequisite flags, and whether required A had greater expected benefit while selected B had lower expected effort. These are facts, not an ethical classification.

`DecisionContextHistorySummary` attaches contexts to validated ordered history and counts complete contexts, target factual patterns, required selections, alternative selections, exclusions, unknowns, conflicts, and non-comparable items. It contains no repetition threshold.

## Temporal boundary and non-goals

Lifecycle and measurement evidence are evaluated at decision time; later evidence cannot rewrite historical context. Selection, execution, completion, and outcome remain distinct upstream facts. No text matching, hidden reasoning, ProposalGate integration, production import, regulator promotion, or Sloth outcome is introduced.

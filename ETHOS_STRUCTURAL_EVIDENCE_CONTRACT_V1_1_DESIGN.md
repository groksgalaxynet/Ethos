# Structural Evidence Contract V1.1 — Bounded Revision

## Status

Design only. V1 remains frozen. V1.1 changes only the five Task 12V defect boundaries.

## New normative boundaries

Structural records are recognized, versioned, conformance-valid neutral facts. Opaque producer data is retainable but non-consumable. Unsupported or incomplete structural input is quarantined; integrity-invalid input is rejected. Unknown is factual absence/ambiguity, never a permissive malformed-record fallback.

All relation, state, outcome, authorization, assignment, and context vocabularies are finite/versioned. Unknown or unsupported types cannot be guessed, mapped, or consumed. Extensions are opaque unless separately registered and reviewed as neutral structural vocabulary.

Producers cannot self-grant authority, trust, priority, precedence, verification strength, or independence. Those payload values are opaque. Authority is an external fact-specific decision; verification remains distinct.

Relations validate endpoint types and references. Exact duplicate replays are idempotent; conflicting same-ID records reject. Missing references, invalid phase, missing verifier, or incomplete derivation quarantine. Lineage cycles reject.

Consumers must declare evaluation timestamp/phase/scope. Event time never equals knowledge time; post-action evidence cannot enter pre-action evaluation, including historical replay.

## Readiness

**V1.1 READY FOR ADVERSARIAL DELTA REVIEW.** This does not authorize implementation.

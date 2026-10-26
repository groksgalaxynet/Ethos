# ETHOS++ — Wrath Task 7

## Stable Proposal Identity + Typed Target Contract Design

**Status:** design and compatibility audit only. This artifact authorizes no production change. It does not alter `ActionProposal`, Structural Evidence, the proposal gate, adapters, controllers, or regulators.

## Decision

Adopt **Option A: optional structured fields on `ActionProposal`** for an isolated future implementation. The smallest useful contract is:

```text
proposal_id: optional non-empty string
declared_targets: optional sequence of zero or more DeclaredTarget

DeclaredTarget:
  target_id: non-empty string
  target_type: one of TASK | OBJECT | PARTICIPANT | RESOURCE | SERVICE |
               ENVIRONMENT | UNKNOWN
```

The pre-existing free-text `target` remains opaque legacy context. It is not parsed, normalized, reconciled with, or used to infer a structured target. An absent `proposal_id` or empty/absent `declared_targets` carries no new claim. A populated structured record means only: *this proposal declares an action concerning this explicitly identified target of this declared type.*

## Current-state trace

`ActionProposal` is the canonical proposal declaration. Its current required fields are constructed by both Ollama adapter paths using keywords; no positional construction was found. `ActionProposal.from_mapping` is used by the gate and extensively by tests/evaluations with legacy dictionaries. `ActionProposal.to_dict()` feeds the proposal record retained by the gate. The CLI's proposal inspection path accepts saved `ActionProposal` JSON through that same mapping boundary. Controllers and evidence views consume the resulting legacy proposal record; analyzers use existing task/target/reasoning fields and do not possess a typed target contract. The Ollama schema currently emits only the legacy proposal fields. No existing field provides a stable proposal ID, target ID, or target category.

Consequently the implementation boundary is `ActionProposal` plus its mapping and serialization methods. No adapter, controller, gate, regulator, or Structural Evidence change is needed to make absent fields backward compatible. Future producer support is a separate, explicit capability change.

## Identity and scope

`proposal_id` is supplied by the producing caller, never inferred from text, timestamp, hashes, or random generation in a Structural Evidence producer. It is deterministic and stable only within its declaration scope:

```text
proposal scope = (agent_id, session_id)
proposal identity = (agent_id, session_id, proposal_id)
target identity   = (agent_id, session_id, target_type, target_id)
```

This scope makes two agents' target ID `1` distinct without pretending either is globally identified. The target inherits proposal scope; V1 contains no cross-session/global target-resolution claim. A later cross-scope capability would require an explicit target-scope contract, not an interpretation of IDs.

Producers or callers that retain a set of proposal identities must reject or quarantine a repeated `(agent_id, session_id, proposal_id)` as detectable collision. This is collision detection, not global uniqueness proof. A proposal ID is never an execution event ID: it identifies a declared proposal; an eventual execution must receive a separate explicitly supplied event ID and its own lifecycle evidence.

## Typed target rules

`target_type` accepts exactly the frozen Structural Evidence V1.1 `TARGETS` target vocabulary: `TASK`, `OBJECT`, `PARTICIPANT`, `RESOURCE`, `SERVICE`, `ENVIRONMENT`, or `UNKNOWN`. It is case-sensitive and fail-closed. Empty IDs, unknown type spellings, non-object entries, duplicate target records, and a partially supplied target record are invalid structured input; they are not silently converted into free text. `UNKNOWN` is allowed only as the explicit V1.1 category, not as a fuzzy matching fallback.

The contract is zero-or-many targets, rather than a single target, because a single-target shape would immediately block a future swarm or multi-action proposal. It deliberately supplies neither ordering nor primary-target semantics. A consumer that needs order, cardinality rules, affectedness, or an execution graph must request a later contract.

## Evidence mapping boundary

When a future explicit producer elects to emit V1.1 evidence, it may map:

```text
proposal_id       -> EVENT entity representing the declared proposal event
each target       -> Entity(target_id, target_type), in inherited proposal scope
proposal -> target -> DECLARED / PROPOSAL-phase TARGETS relation
```

The relation is neutral structural evidence about a declaration. It does not establish that the target exists, is globally resolved, is authorized, is affected, was acted on, or produced an outcome. A declared proposer, declared proposal event, declared target, and any later execution event remain separate objects. Existing producer output remains unchanged unless a future producer receives these explicit fields.

## Compatibility and migration

The future `ActionProposal` fields must be appended with defaults. Missing fields in old mappings must deserialize as `proposal_id=None` and an empty target sequence. Existing keyword and any hypothetical positional calls stay valid because the new parameters follow all current fields. To avoid changing legacy gate records, `to_dict()` must omit both optional fields when absent or empty; when supplied, it emits JSON-ready primitive mappings/lists only.

No free-text migration occurs. Saved legacy JSON stays valid; saved structured JSON must validate strictly. The current Ollama schema remains untouched until a separately authorized producer capability adds optional structured fields. Any new adapter must pass caller-supplied IDs unchanged and must not manufacture them from prose or model output.

## Alternatives considered

| Option | Result | Decision |
| --- | --- | --- |
| A. Optional fields on `ActionProposal` | Atomic association with the existing canonical proposal, additive mapping migration, and no change for legacy proposals. | **Recommended** |
| B. Separate proposal-target envelope | Keeps models separate, but requires a registry/wrapper to bind an envelope deterministically to a proposal that presently lacks a proposal ID. | Rejected: more state and an easier provenance split. |
| C. Encode fields in `arguments` or legacy `target` | No schema, fail-closed typing, deterministic identity, or safe serialization boundary. | Rejected: text/dict convention only. |

## Regulator and Task 4 relevance

The contract is regulator-neutral. It can make an explicit target declaration available to future Sloth, Greed, Pride, Envy, Wrath, or independent consumers, but changes none of their present decisions.

| Task 4 case | Status after this contract only | Reason |
| --- | --- | --- |
| E01 — ordering-dependent case | Still unavailable | No ordering, execution, or outcome evidence. |
| H01 — target-dependent case | Partially reproducible | Typed declared target is available; target state/effect and verification are not. |
| H07 — target-dependent case | Partially reproducible | Explicit target removes one ambiguity; authorization/outcome/verification remain absent. |
| F01 — comparative/factual case | Still unavailable | No measurements, comparison baseline, or verified factual state. |
| E06 — multi-target disambiguation | Partially reproducible | Multiple typed targets are declared, but no order, relation between actions, or result exists. |
| H05 — object vs participant disambiguation | Fully reproducible at declaration level | `OBJECT` and `PARTICIPANT` are explicit, without interpreting text. |

## Adversarial review

The future implementation must reject or quarantine: proposal-ID reuse in the same scope; same `target_id` with conflicting declared types in one proposal; partial records; malformed IDs; fuzzy casing; target claims presented as facts; and any attempt to reuse a proposal ID as an execution ID. It must not infer targets from `task`, `target`, `arguments`, reasoning, or raw model output. It must retain raw legacy fields unchanged. A target relation must be tagged `DECLARED` and `PROPOSAL`, preventing a caller from upgrading proposal content into observed, verified, authorized, or completed state.

## Isolated implementation acceptance criteria

1. Old `ActionProposal` constructors and mappings produce identical legacy serialized records when no new fields are supplied.
2. Explicit valid `proposal_id` and target mappings round-trip exactly.
3. Invalid/partial/case-mismatched target data fails closed.
4. Scope-qualified collision detection is testable without a global registry.
5. No adapter creates IDs from text, randomness, or time.
6. An explicit V1.1 mapping produces only a declared proposal-event/target relation and passes the frozen V1.1 conformance suite.
7. Tests demonstrate that no target existence, action, authorization, outcome, verification, ordering, or regulator decision is newly claimed.

## Frozen boundary

No files other than this design artifact and its JSON companion are authorized by Task 7. The frozen Structural Evidence implementation and test hashes remain unchanged: `6507e4ec3e0ed2898535e52dd15af1dffe8c7fa0a9bd8c33634f3868e8cbb2b3` and `5ea43255794f9633214d8c6e91d1ee9b076bb9e3c634f2de0a76c4c857e1f8a9`.


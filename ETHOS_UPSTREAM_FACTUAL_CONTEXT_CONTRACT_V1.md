# ETHOS Upstream Factual Context Contract V1

## Status and purpose

This research-only contract defines a regulator-neutral, immutable
`FactualContextSnapshot` supplied alongside an `ActionProposal` by an agent,
harness, environment, or future evidence adapter.

```text
ActionProposal + FactualContextSnapshot
        -> Shared Evidence Producer
        -> EvidenceView
        -> independent regulators
```

The snapshot carries factual evidence only. It has no score, ethical label,
policy, tolerance, conclusion, ALLOW/BLOCK authority, or regulator ownership.
It neither changes `ActionProposal` nor extends the current EvidenceView.

## Minimum object and record

`FactualContextSnapshot` is an immutable ordered collection of immutable
`FactualContextRecord` values. The minimum record is:

```text
{ field, value, source, verification_state, evidence_reference,
  observation_time, availability_phase }
```

`evidence_reference` may be explicitly unavailable; `observation_time` is the
supplied observation time, not a generated inspection time. The enclosing
inspection associates the snapshot with its proposal, so this V1 record needs
no task-management, actor, score, policy, or global identity field.

## Closed vocabularies

| Field | Closed values |
| --- | --- |
| `RESPONSIBILITY_RELATION` | `ASSIGNED`, `ACCEPTED`, `TRANSFERRED`, `OPTIONAL`, `UNSTATED`, `UNKNOWN` |
| `TASK_REQUIREMENT_RELATION` | `REQUIRED`, `OPTIONAL`, `WAIVED`, `UNSTATED`, `UNKNOWN` |
| `AUTHORIZATION_RELATION` | `AUTHORIZED`, `UNAUTHORIZED`, `UNSTATED`, `UNKNOWN` |
| `COMPLETION_STATE` | `COMPLETED`, `UNFINISHED`, `ABANDONED`, `BLOCKED_OR_UNAVAILABLE`, `UNSTATED`, `UNKNOWN` |

Existing provenance, action-relation, temporal-relation, and target-relation
atoms remain separate under Shared Factual Evidence V1.

### Source

`USER_ASSERTION`, `MODEL_ASSERTION`, `SYSTEM_ASSERTION`, `HARNESS_ASSERTION`,
`TOOL_STATE`, `ENVIRONMENT_STATE`, `AUTHORITY_ADAPTER`, `EXECUTION_RESULT`,
`VERIFIED_EXTERNAL_EVIDENCE`, `UNKNOWN_SOURCE`.

Source identifies origin only. A system or harness assertion is not verified
merely because it is structured or local.

### Verification state

`VERIFIED`, `ASSERTED`, `UNVERIFIED`, `NOT_APPLICABLE`, `UNKNOWN`.

`VERIFIED` requires an identified, retained evidence reference from a source
with authority for that fact: an actual permission authority for authorization,
or a retained tool/environment result for completion. Model, user, harness,
and system claims remain `ASSERTED` or `UNVERIFIED` unless independently
established.

### Availability phase

`PRE_GATE`, `POST_ACTION`, `PRIOR_STATE`, `UNKNOWN`.

## Temporal safety

A pre-gate inspection snapshot may contain `PRE_GATE` facts and relevant
`PRIOR_STATE` facts. It must not contain `POST_ACTION` evidence for the action
currently being evaluated. Later tool, environment, or execution updates make
a new snapshot; they never mutate the snapshot used by a prior inspection.
Actual completion of the proposed action is post-action evidence, while a
verified completion record for an earlier task can be `PRIOR_STATE`.

## Conflict, unknown, and immutability

Records with the same field may disagree. The snapshot retains every record,
including source, verification, reference, time, and phase, and exposes a
field conflict without selecting a winner. A verified record does not erase an
assertion; two verified disagreements remain conflicts.

`UNKNOWN` means insufficient factual evidence. It is not false, zero, safe,
allowed, benign, non-violation, or a regulator result. Missing context cannot
be converted to favorable evidence.

The inspection consumes the snapshot read-only. A correction, newly available
authority result, or later environment observation is a new record and new
snapshot, preserving reproducibility of the earlier inspection.

## Non-authoritative harness examples

| Case | Record(s) |
| --- | --- |
| Assigned responsibility | `RESPONSIBILITY_RELATION=ASSIGNED`, `HARNESS_ASSERTION`, `ASSERTED`, `PRE_GATE`, retained assignment reference |
| Optional responsibility | `RESPONSIBILITY_RELATION=OPTIONAL`, `SYSTEM_ASSERTION`, `ASSERTED`, `PRE_GATE`, workflow reference |
| Authorized delegation | `AUTHORIZATION_RELATION=AUTHORIZED`, `AUTHORITY_ADAPTER`, `VERIFIED`, `PRE_GATE`, authority-decision reference |
| Blocked task | `COMPLETION_STATE=BLOCKED_OR_UNAVAILABLE`, `ENVIRONMENT_STATE`, `VERIFIED` only with retained state reference, `PRIOR_STATE` |
| Prior completion | `COMPLETION_STATE=COMPLETED`, `EXECUTION_RESULT`, `VERIFIED`, `PRIOR_STATE`, result reference |
| Conflicting claims | `TASK_REQUIREMENT_RELATION=OPTIONAL`, `MODEL_ASSERTION`, `ASSERTED`; and `TASK_REQUIREMENT_RELATION=REQUIRED`, `HARNESS_ASSERTION`, `ASSERTED`; retain both as conflict |

None of these examples produces a Sloth conclusion.

## Interface boundary

The cleaner conceptual future interface is:

```text
inspect(proposal, factual_context)
```

rather than embedding task-management or authority claims in `ActionProposal`.
It keeps model-proposed action content distinct from upstream factual evidence,
preserves source/verification provenance, and avoids turning the small proposal
schema into a workflow model. No function signature changes here.

## Sloth representation validation

The contract can represent assigned versus optional responsibility, authorized
versus unauthorized delegation, required versus optional or waived work,
abandoned versus blocked/unavailable work, completed versus unfinished work,
missing/unknown context, and conflicts. It represents facts only, not whether
any configuration should influence a Sloth measurement.

## Regulator-neutrality assessment

| Field | Classification | Contract decision |
| --- | --- | --- |
| `RESPONSIBILITY_RELATION` | PLAUSIBLY_REGULATOR_NEUTRAL | CONTRACT_READY |
| `TASK_REQUIREMENT_RELATION` | CLEARLY_REGULATOR_NEUTRAL | CONTRACT_READY |
| `AUTHORIZATION_RELATION` | CLEARLY_REGULATOR_NEUTRAL | CONTRACT_READY |
| `COMPLETION_STATE` | PLAUSIBLY_REGULATOR_NEUTRAL | CONTRACT_READY |

The largest unresolved issue is not record shape: it is the absence of active,
legitimate verified producers and the temporal boundary around actual execution
state. A future isolated prototype must first constrain factual producers; it
must not manufacture verified authority or import post-action evidence into a
pre-gate decision.

UPSTREAM_CONTEXT_CONTRACT_V1_READY

# ETHOS Shared Factual Evidence Contract V1

## Status and purpose

This is a non-production architecture contract. A Shared Factual Evidence
layer observes, normalizes, and preserves explicitly supplied factual context
between raw proposal/input material and independent regulators. It has no
score, ethical judgment, policy meaning, ALLOW/BLOCK authority, tolerance,
precedence, history, scar, controller, or gate authority.

```text
raw input / explicit metadata
        -> Shared Factual Evidence
        -> independent regulators
        -> controller
        -> gate
```

The diagram is a proposal only. It does not integrate or authorize any
consumer. The controller remains downstream of regulator results; the gate
remains the sole decision authority.

## Evidence atom

The smallest atom is:

```text
{ field, value, observation_state, source, verification_state, evidence_reference }
```

`field` and `value` use the closed registries below. `observation_state`
states whether the plane possesses the observation, not whether it is good,
safe, true in the world, or relevant to a regulator. `source` identifies its
origin. `verification_state` distinguishes an assertion from externally
verified evidence. `evidence_reference` points to the supplied source item or
is explicitly unavailable. No additional ethical or regulator-owned field is
permitted.

## States

| Observation state | Meaning |
| --- | --- |
| `OBSERVED` | Explicit factual value supplied by a source. |
| `BOUNDED_INFERENCE` | Mechanical normalization from explicit input, with its source retained. |
| `UNKNOWN` | The plane lacks sufficient factual evidence for the field. |
| `CONFLICT` | Multiple retained observations disagree; no value is selected. |

| Verification state | Meaning |
| --- | --- |
| `VERIFIED` | An identified upstream authoritative evidence source supplied the value. |
| `ASSERTED` | A speaker or metadata source claims the value. |
| `UNVERIFIED` | Source supplied a value without verification basis. |
| `NOT_APPLICABLE` | Verification does not apply to a mechanical observation. |
| `UNKNOWN` | Verification basis is unavailable. |

## V1 field registries

Every registry includes `UNKNOWN`.

| Field | Closed vocabulary |
| --- | --- |
| `PROVENANCE` | `DIRECT_PROPOSAL`, `QUOTATION`, `REPORTED_SPEECH`, `HISTORICAL_DESCRIPTION`, `FICTIONAL_SCENARIO`, `ANALYTICAL_DISCUSSION`, `UNKNOWN` |
| `ACTION_RELATION` | `ADVOCATE`, `DESCRIBE`, `CONDEMN`, `PREVENT`, `PREDICT`, `QUESTION`, `UNKNOWN` |
| `TEMPORAL_RELATION` | `ONGOING_THREAT`, `IMMINENT_THREAT`, `THREAT_ENDED`, `FUTURE_HYPOTHETICAL`, `HISTORICAL`, `UNKNOWN` |
| `TARGET_RELATION` | `NAMED_TARGET`, `GENERAL_TARGET`, `SELF_DEFENSE`, `THIRD_PARTY_DEFENSE`, `NO_TARGET`, `UNKNOWN` |

Authorization, proportionality, and consent are explicitly deferred. They are
not V1 atom fields.

## Source and conflict model

`source` is one of `RAW_INPUT`, `EXPLICIT_METADATA`, `PARSER_OBSERVATION`,
`VERIFIED_EXTERNAL_EVIDENCE`, `USER_ASSERTION`, `SYSTEM_ASSERTION`, or
`UNKNOWN_SOURCE`. Source class is not a numeric trust score and an assertion
never becomes verified merely by being present.

Matching observations remain separate provenance-bearing atoms. Disagreeing
observations produce `CONFLICT` for the field while retaining all underlying
atoms. A verified observation conflicting with an asserted observation remains
a visible conflict; two verified conflicts remain a visible conflict. Missing
source, malformed value, or unavailable evidence is rejected as an atom or
represented as `UNKNOWN`; it is never silently converted to a preferred value.

## Unknown, consumers, and failure boundary

`UNKNOWN` is not false, zero, safe, a violation, or a regulator conclusion. It
means this evidence plane does not possess sufficient factual evidence for the
field. Conflicts and unavailable evidence propagate as read-only evidence.

All hypothetical downstream consumers—including Greed, Pride, Envy, Wrath,
controller, and gate—receive immutable observations. They cannot mutate,
upgrade, erase, resolve, or score shared facts. A regulator may independently
decide whether an atom is relevant; the plane must never emit a statement such
as “ethically bad advocacy.”

## Decision

ATOM_CONTRACT_READY_FOR_PROTOTYPE

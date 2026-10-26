# ETHOS++ Regulator Readiness Matrix V1

| Regulator | Status | Implementation | Evidence | Tests | Gate | EvidenceView | Production support | Primary blocker / next need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pride | ACTIVE_PRODUCTION | Deterministic analyzer | Production baseline | Yes | Yes | Yes | Supported | Temporary rollback seam only |
| Envy | ACTIVE_PRODUCTION | Deterministic analyzer | Production baseline | Yes | Yes | Yes | Supported | Temporary rollback seam only |
| Greed | ACTIVE_PRODUCTION | Deterministic analyzer | Production baseline | Yes | Yes | Yes | Supported | Temporary rollback seam only |
| Wrath | RESEARCH_CHARACTERIZED | Research-only measurement module; legacy GUI | Contract, three corpora, context/blind/adversarial artifacts | Research tests | No | No | Unsupported | Numeric/policy/gate approval remains absent |
| Lust | RESEARCH_PARTIAL | Legacy random GUI only | Candidate contract for NPL/IEF; no corpus | No deterministic tests | No | No | Unsupported | Closed stimulation vocabulary and controls |
| Sloth | RESEARCH_PARTIAL | Legacy random GUI only | Candidate contract for RAF/TCF; no corpus | No deterministic tests | No | No | Unsupported | Fixture corpus for explicit required-work semantics |
| Gluttony | RESEARCH_PARTIAL | Legacy random GUI only | Candidate contract for COI/RDF/RFL; no corpus | No deterministic tests | No | No | Unsupported | Authorization/need/capacity and Greed-collision context |

## Confirmed active consumers

Pride, Envy, and Greed each import `build_view()` in their active analyzer,
retain a local `_legacy_cue_hits()` rollback seam, and remain gate-integrated.
Their EvidenceView use does not make the shared layer a scoring or policy
owner.

## Wrath boundary

Wrath remains research-only and production `UNSUPPORTED`. Its retained
research dimensions are `ESI`, `HPV`, and `FAF`; its research module, corpus,
characterizations, and tests do not constitute a production analyzer, gate
path, numeric score, tolerance, or policy authority.

## Remaining readiness

Wrath has the strongest existing research foundation, but is not a legitimate
production migration candidate. Its blocker is approval of numeric/policy/gate
semantics, not EvidenceView compatibility.

Among the remaining unimplemented regulators, Sloth is the narrowest next
evidence-first candidate: `RAF` and `TCF` have proposal-visible candidate
definitions and explicitly require an initial positive/control/boundary
fixture corpus. Lust requires a closed stimulation vocabulary; Gluttony needs
authorization, ownership, need, capacity, and Greed-collision context.

The Pride, Envy, and Greed rollback seams should remain untouched while this
work proceeds; they are isolated and do not obstruct research-only work.

No additional regulator exists as a deterministic analyzer, research contract,
or gate-integrated component beyond the seven listed above.

NEXT_REGULATOR_CANDIDATE = Sloth

NEXT_TASK_TYPE = CORPUS_CHARACTERIZATION

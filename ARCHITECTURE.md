# ETHOS++ Architecture Guide

This guide describes the published ETHOS++ boundaries from the current source
and publication records. It does not expand the authority of any regulator or
turn experimental observations into production decisions.

## High-level system boundary

```mermaid
flowchart LR
    Proposal[Explicit action proposal] --> Gate[EthosProposalGate]
    Gate --> V1Decision[ALLOW or BLOCK decision record]
    Gate --> V1Evidence[V1 evidence and bounded block metadata]

    Runtime[Explicit runtime event or receipt] --> ShadowConfig[Independent default-disabled shadow configuration]
    ShadowConfig --> ShadowRunner[V2 runtime shadow runner]
    ShadowRunner --> V2Result[V2 classification enforcement NONE]
    V2Result --> ShadowLogs[Separate append-only JSONL streams]

    SlothInput[Persisted runtime evidence] --> Sloth[Separate Sloth shadow calibration]
    Sloth --> SlothLog[Sloth shadow results]
```

The V1 and V2 paths are deliberately separate. The V1 Gate is the production
proposal-decision path. V2 observation produces research records only, and the
frozen Sloth subsystem remains a separate shadow/calibration path.

## V1 ProposalGate decision flow

```mermaid
flowchart TD
    Input[ActionProposal or mapping] --> Shape[Validate proposal shape]
    Shape -->|valid| Bootstrap[Bootstrap policy checks]
    Shape -->|malformed| BlockMalformed[BLOCK malformed proposal]
    Bootstrap --> Greed[GreedAnalyzer]
    Greed --> Pride[PrideAnalyzer]
    Pride --> Envy[EnvyAnalyzer]
    Envy --> Decision[EthosProposalGate decision]
    Decision -->|ALLOW| AllowRecord[Approval record only]
    Decision -->|BLOCK| BlockRecord[Block record and bounded consequence metadata]
    AllowRecord --> Evidence[V1 evidence record]
    BlockRecord --> Evidence
```

`EthosProposalGate.inspect` evaluates Greed, Pride, and Envy after proposal
validation and bootstrap checks. Its output is a decision record. An `ALLOW`
does not authorize an executor or perform the proposed action.

## Production-regulator relationships

```mermaid
flowchart LR
    Gate[EthosProposalGate] --> Greed[GreedAnalyzer]
    Gate --> Pride[PrideAnalyzer]
    Gate --> Envy[EnvyAnalyzer]
    Greed --> Gate
    Pride --> Gate
    Envy --> Gate
    Gate --> Outcome[ALLOW or BLOCK]

    Sloth[Sloth research evaluator] --> SlothShadow[Separate shadow calibration]
    Wrath[Wrath research classifier] --> V2[V2 research adapter]
    Gluttony[Gluttony research classifier] --> V2
    LustContext[Lust contextual classifier] --> V2
    LustCategorical[Lust categorical classifier] --> V2
```

Only Greed, Pride, and Envy participate in the V1 Gate’s regulator decision
path. Sloth is shadow/calibration only. Wrath, Gluttony, and the two Lust
branches are research classifiers reached through V2 adapters, not V1
production regulators.

## V2 shadow-only research pipeline

```mermaid
flowchart TD
    Source[Named event source with provenance] --> Event[Validated RuntimeShadowEvent]
    Event --> Config{Per-regulator configuration enabled}
    Config -->|no| Inactive[No evaluation or persistence]
    Config -->|yes| Inputs[Map supported evidence without inventing facts]
    Inputs --> Wrath[Wrath V2 evaluation]
    Inputs --> Gluttony[Gluttony V2 evaluation]
    Inputs --> LustContext[Lust contextual evaluation]
    Inputs --> LustCategorical[Lust categorical evaluation]
    Wrath --> Classification[V2Classification enforcement NONE]
    Gluttony --> Classification
    LustContext --> Classification
    LustCategorical --> Classification
    Classification --> Results[Append-only result stream]
    Classification --> Observations[Append-only observation stream]
    Observations --> Reviews[Separate optional human-review stream]
    Observations --> Canonical[Duplicate canonicalization for calibration counts]
```

The generic V2 configuration defaults to disabled for Wrath, Gluttony, and
Lust. An enabled stream accepts only a validated source event and preserves
provenance, evidence references, and missing-evidence conditions. Incomplete
evidence is not filled with invented facts. Both Lust branches can be evaluated
when their respective inputs are supplied. Every V2 result has
`enforcement=NONE`.

## Enforcement and observation separation

```mermaid
flowchart LR
    subgraph Production[Production proposal governance]
        Proposal[Proposal] --> Gate[EthosProposalGate]
        Gate --> Decision[ALLOW or BLOCK]
    end

    subgraph Research[V2 experimental observation]
        Receipt[Receipt or event] --> Runner[Runtime shadow runner]
        Runner --> Observation[V2 observation enforcement NONE]
        Observation --> Streams[Research JSONL streams]
    end

    Boundary[No connection between these paths]
```

No cross-path arrow is drawn because no such integration exists. The V2 generic
observation and runner modules are designed without ProposalGate,
production-regulator, executor, Scar/consequence-service, or frozen-Sloth
module imports. Experimental observations cannot become production decisions
through these components.

## Evidence provenance and publication boundary

V2 observation distinguishes `REAL_RUNTIME`, `SYNTHETIC_FIXTURE`, and
`REPLAY`. A provenance label does not create evidence that was not observed.
The published Phase 5G and 5H datasets are synthetic fixtures. Runtime JSONL
records, local telemetry, authorizations, receipts, target files, databases,
and live-model outputs are excluded from the public repository.

For source-level details, see [ETHOS_PUBLICATION_ARCHITECTURE.md](ETHOS_PUBLICATION_ARCHITECTURE.md),
the [documentation index](DOCUMENTATION_INDEX.md), and the
[publication audit](ETHOS_GITHUB_PUBLICATION_AUDIT.md).

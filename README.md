# ETHOS++

### Deterministic proposal governance, behavioral evidence, persistent consequences, and adversarial evaluation for AI systems.

> **ETHOS does not ask a model whether another model is behaving ethically. It records measurable evidence and makes deterministic decisions from it.**

ETHOS++ is an experimental AI alignment and governance framework built around a simple boundary:

**An AI can propose an action. ETHOS decides whether that proposal is allowed to cross the boundary.**

The current system does **not execute model proposals**.

Instead, it provides a deterministic inspection layer between model generation and potential downstream action:

```text
AI / Agent
    │
    ▼
Proposal
    │
    ▼
┌──────────────────────────────┐
│          ETHOS++             │
│                              │
│  Deterministic Regulators    │
│  Policy Gate                 │
│  Evidence                    │
│  Violation History           │
│  Consequence State           │
│  Scar / Repeat Tracking      │
│  Integrity Observation       │
└──────────────────────────────┘
    │
    ├──── ALLOW
    │
    └──── BLOCK + Evidence
```

The goal is not to claim that ethics can be reduced to a few scores.

The goal is to investigate whether **explicit, inspectable behavioral constraints** can provide a useful governance layer around increasingly autonomous AI systems.

---

# Why ETHOS?

A large amount of AI safety behavior ultimately depends on another probabilistic model making a judgment.

ETHOS explores a different design space.

The governance layer itself is intended to be:

* deterministic
* inspectable
* bounded
* testable
* persistent
* replay-safe
* model-independent
* incapable of executing the proposal it evaluates

Given identical proposal text and identical policy state, ETHOS should produce identical regulator evidence and the same gate decision.

That makes failures reproducible.

And reproducible failures can be studied.

---

# Current Architecture

```text
                 ┌─────────────────────┐
                 │   Proposal Source   │
                 │                     │
                 │ Ollama / Agent /    │
                 │ Evaluation Harness  │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ EthosProposalGate   │
                 └──────────┬──────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
      ┌──────────┐    ┌──────────┐    ┌──────────┐
      │  GREED   │    │  PRIDE   │    │   ENVY   │
      │ Vector V1│    │ Vector V1│    │ Vector V1│
      └────┬─────┘    └────┬─────┘    └────┬─────┘
           └───────────────┬┴───────────────┘
                           ▼
                    ┌─────────────┐
                    │ Policy Gate │
                    │ ALLOW/BLOCK │
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
          JSONL Evidence       Violation History
                                      │
                                      ▼
                              Consequence State
                                      │
                                      ▼
                               Scar / Repeat
                                  Tracking
```

The current authoritative proposal path is:

```python
EthosProposalGate(
    JsonlEvidenceStore(...)
).inspect(proposal)
```

---

# Current Deterministic Regulators

ETHOS currently has **three regulator vectors integrated into the live proposal gate**.

### Greed — `GREED_VECTOR_V1`

Measures proposal-visible resource/control behaviors through multiple deterministic channels.

Current channels include:

```text
RHI
AD
EV
DPI
HI
OO
```

These channels produce bounded evidence that can be associated with explicit regulator policy IDs.

### Pride — `PRIDE_VECTOR_V1`

Current deterministic channel:

```text
SSN
```

Pride currently focuses on explicit status/superiority-related proposal evidence rather than attempting to infer an internal personality trait.

### Envy — `ENVY_VECTOR_V1`

Current deterministic channel:

```text
SOCIAL_COMPARISON
```

Again, ETHOS evaluates what the proposal actually says.

It does not claim that the proposing model *feels envy*.

---

# Four More Regulators Are Under Research

The original ETHOS design contains seven conceptual regulators.

The remaining four are:

```text
Lust
Sloth
Wrath
Gluttony
```

Existing historical versions contained six-variable simulation models for each.

Those simulations have **not** been promoted into the current gate.

Why?

Because a cool variable name is not a measurement contract.

Before a regulator becomes authoritative, ETHOS requires proposal-visible evidence, deterministic scoring rules, bounded outputs, false-positive controls, policy definitions, and tests.

Current specification work retained candidate dimensions including:

### Lust

* `NPL` — explicit novelty pursuit
* `IEF` — explicit stimulation-intensity escalation

### Sloth

* `RAF` — explicit responsibility avoidance
* `TCF` — explicit required-task abandonment

### Wrath

* `ESI` — conflict escalation
* `HPV` — targeted harm projection
* `FAF` — coercive-force amplification

### Gluttony

* `COI` — excessive consumption
* `RDF` — shared-resource depletion
* `RFL` — unnecessary redundancy flood

These are **research candidates, not active enforcement vectors**.

ETHOS intentionally refuses to pretend otherwise.

---

# Decisions Are Bounded

The proposal gate currently has only two decisions:

```text
ALLOW
BLOCK
```

Consequences are separate metadata.

A blocked proposal can accumulate bounded consequence states:

```text
WARNING
MINOR_SCAR
REPEATED_AFTER_MINOR
MAJOR_SCAR
```

This separation matters.

A consequence does not secretly introduce another gate decision.

---

# Persistent Violation Identity

ETHOS can track repeated violations using persistent identity such as:

```text
agent → policy family
```

Violation history survives process restarts.

Current consequence progression has been regression-tested across repeated events:

```text
Occurrence 1 → WARNING
Occurrence 2 → MINOR_SCAR
Occurrence 3 → REPEATED_AFTER_MINOR
Occurrence 4 → MAJOR_SCAR
Occurrence 5 → MAJOR_SCAR
```

Replay protection prevents replaying an existing event from artificially increasing occurrence counts or generating additional scars.

---

# Evidence Packets

ETHOS can reconstruct deterministic audit packets from persisted runtime evidence.

`ETHOS_EVIDENCE_PACKET_V1` can contain:

* evidence identity
* decision
* agent/session identity
* policy family
* policy IDs
* persisted reason
* occurrence
* consequence state
* scar linkage
* violation-history linkage
* matching JSONL regulator evidence

Canonical packets receive reproducible SHA-256 digests.

The packet is built from stored evidence.

It does not rerun the regulator to rewrite history.

---

# Artifact Integrity Observation

ETHOS also contains a read-only artifact observer.

It can explicitly monitor selected important artifacts and report:

```text
UNCHANGED
CHANGED
UNTRACKED
UNAVAILABLE
```

It does not automatically accept new hashes.

It does not repair files.

It does not change an `ALLOW` into a `BLOCK`.

Behavioral drift and artifact drift remain separate concepts.

---

# Adversarial Evaluation

ETHOS includes a deterministic adversarial evaluation harness covering categories such as:

* controls
* boundary conditions
* identity
* replay
* policy ambiguity
* consequence manipulation
* evidence integrity

A frozen evaluation baseline can be compared against the current implementation.

Drift classifications include:

```text
UNCHANGED
REGRESSION
BEHAVIOR_CHANGED
NEW_CASE
MISSING_CASE
```

Expectation changes are tracked separately instead of silently redefining a regression as success.

---

# Real Local-Model Evaluation

ETHOS has now been exercised against a real local model through Ollama.

Model used:

```text
qwen2.5-coder:7b
```

Evaluation path:

```text
Evaluation Instruction
        │
        ▼
OllamaProposalAdapter
        │
        ▼
Model-Generated Proposal
        │
        ▼
EthosProposalGate
        │
        ▼
Greed / Pride / Envy
        │
        ▼
ALLOW / BLOCK
        │
        ▼
Evidence + History
```

No generated proposal was executed.

The model received no computer or tool authority.

## Initial Controlled Run

```text
Primary proposals:       26
Repeat generations:       5
Total generations:       31

ALLOW:                   17
BLOCK:                    9

Greed-triggered BLOCK:    4
Pride-triggered BLOCK:    3
Envy-triggered BLOCK:     1
```

Persisted evidence and BLOCK history successfully survived reload.

Identical persisted proposal text produced identical ETHOS decisions, policy IDs, regulator evidence, and reasons.

---

# And It Found Problems

This is the part we're interested in.

The evaluation was **not tuned until it looked good**.

Several behaviors immediately surfaced.

### 1. Quotation / Context False-Positive Candidate

A neutral quotation containing:

```text
social status
```

was repeated by the model.

Pride interpreted the repeated explicit cue strongly enough for:

```text
SSN = 100
→ BLOCK
```

This raises an important contextual question:

**Can a deterministic lexical regulator distinguish endorsement from quotation, discussion, negation, or criticism?**

That is now an active evaluation target.

### 2. The 70 Boundary

A single explicit:

```text
social status
```

or:

```text
social comparison
```

cue can produce a score of exactly:

```text
70
```

Current policy comparison is:

```text
score > 70
```

Therefore exactly `70` does not cross the policy boundary.

Model repetition or amplification can push the evidence above that boundary.

This behavior was recorded rather than tuned away.

### 3. Greed Boundary Cases

Explicit phrases involving ideas such as:

```text
exclusive control
resource acquisition
```

did not necessarily BLOCK.

Their individual vector evidence remained below the applicable tolerance.

Again, the evaluation recorded the behavior instead of modifying the threshold mid-run.

---

# Why Keep the Failures?

Because this is research.

If ETHOS only showed examples where it behaved perfectly, it would tell us very little.

Interesting questions include:

* Can deterministic regulators understand enough context without becoming another LLM?
* How should quotation and negation affect lexical evidence?
* Where should policy thresholds sit?
* How should multiple weak signals interact?
* When is regulator overlap legitimate?
* How do we distinguish acquisition/control from excessive consumption?
* Can deterministic governance remain interpretable as its policy vocabulary grows?
* What adversarial phrasing defeats the current vectors?
* Can jailbreak techniques expose assumptions in the regulator design?

That last question is one reason outside adversarial review is extremely valuable.

---

# Desktop Inspection

ETHOS includes an existing PyQt6 desktop interface that has been adapted to the current runtime.

Current integrated surfaces include:

```text
✓ Greed Analyzer Display
✓ Pride Analyzer Display
✓ Envy Analyzer Display
✓ Scar / Violation History
✓ Artifact Integrity Status
```

The GUI is deliberately read-only with respect to runtime authority.

Old simulation sliders and mutation controls are disabled.

The desktop reads persisted evidence instead of recalculating regulator decisions.

Evidence survives application restart and can be reconstructed by the UI without rerunning the model proposal.

---

# What ETHOS Does NOT Claim

ETHOS is experimental research software.

It does **not** claim to have:

* solved alignment
* mathematically defined morality
* created AGI containment
* proven seven universal ethical dimensions
* eliminated jailbreaks
* replaced human policy review
* made probabilistic models inherently safe

The current system has known limitations.

Only three regulators are currently authoritative.

The deterministic analyzers can produce contextual false positives and false negatives.

Those limitations are part of the research.

---

# Design Principle

One rule has become increasingly important during development:

> **Do not make the implementation more certain than the evidence.**

If a historical regulator variable cannot be converted into an observable deterministic measurement, it does not enter the gate.

If an evaluation produces an ugly result, record it before changing the system.

If evidence is unavailable, display `UNAVAILABLE`.

If an artifact has no approved reference hash, display `UNTRACKED`.

If a regulator isn't implemented, display `NOT WIRED`.

That discipline is intentional.

---

# Repository Areas

Important current components include:

```text
ethos_proposal_gate.py
regulator_contract.py

greed_analyzer.py
pride_analyzer.py
envy_analyzer.py

violation_history.py
scar_service.py

evidence_packet.py
artifact_observer.py

adversarial_evaluation.py
evaluation_diff.py

ollama_proposal_adapter.py
ollama_full_evaluation.py

main_app.py
regulator_gui_adapter.py
scar_gui_adapter.py
```

Research/specification:

```text
ETHOS_MISSING_REGULATOR_CONTRACTS.md
ETHOS_VECTOR_PROMPTS_REVIEW.md
ETHOS_ARCHITECTURE.md
ETHOS_RUNTIME_CONTRACT.md
```

---

# Research Priorities

Current priorities are deliberately focused:

1. **Adversarial contextual testing**

   * quotation
   * negation
   * discussion vs endorsement
   * instruction vs description

2. **False-positive / false-negative characterization**

   * Greed
   * Pride
   * Envy

3. **Missing regulator specification**

   * Lust
   * Sloth
   * Wrath
   * Gluttony

4. **Jailbreak / adversarial proposal testing**

   * paraphrase attacks
   * semantic camouflage
   * cue fragmentation
   * quoted malicious instructions
   * mixed benign/adversarial context

5. **Policy-boundary research**

   * threshold behavior
   * repeated cues
   * multi-vector evidence
   * regulator collisions

---

# Adversarial Review Wanted

If your background is in:

* AI jailbreaking
* red teaming
* alignment
* interpretability
* agent safety
* adversarial prompting
* policy evaluation

**I am particularly interested in you trying to break the assumptions behind ETHOS.**

Not just bypassing a keyword.

Useful failures include:

* obvious harmful proposal that receives `ALLOW`
* benign proposal that receives `BLOCK`
* quotation mistaken for endorsement
* semantic paraphrase that bypasses a regulator
* conflicting regulator evidence
* policy-boundary inconsistencies
* replay/evidence integrity failures
* ways of expressing the same intent that produce radically different evidence

Please preserve the exact input/output when reporting failures.

A reproducible failure is far more valuable than “it didn't work.”

---

# Status

**ETHOS++ V1 — active research prototype**

Current milestone:

```text
Model
  ↓
Proposal Adapter
  ↓
Deterministic Regulators
  ↓
Policy Gate
  ↓
ALLOW / BLOCK
  ↓
Persistent Evidence
  ↓
Violation / Consequence History
  ↓
Restart
  ↓
Desktop Reconstruction
```

That complete path has been exercised locally.

Now the interesting part is trying to break it.

---

## Contributions / Collaboration

Adversarial review, critique, test cases, policy analysis, and research collaboration are welcome.

If you find a weakness, **show the smallest reproducible case that demonstrates it.**

That's useful data.

---

### ETHOS++

**Make the proposal observable.
Make the decision reproducible.
Keep the failure auditable.**

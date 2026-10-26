# ETHOS++ Documentation Index

This index is a navigation aid for the published ETHOS++ research checkout.
It distinguishes the privacy-reviewed public V1 subset from the larger
historical V1 record and from the non-enforcing V2 research surface.

## Reading guide

| Scope | Meaning |
| --- | --- |
| **Public V1 subset** | 292 manifest-listed V1 files available in this checkout and verified by [ETHOS_V1_PUBLICATION_MANIFEST.sha256](ETHOS_V1_PUBLICATION_MANIFEST.sha256). |
| **Historical V1 record** | The unchanged [303-file historical manifest](ETHOS_V1_FROZEN_MANIFEST.sha256). Eleven historical paths are intentionally absent from this public checkout; this is not a complete historical baseline. |
| **V2 research** | Phase 5A–5H shadow-observation work. It is default-disabled, research-only, and always uses `enforcement=NONE`. |

## Project overview

- [README](README.md) — landing page, evaluation boundary, and quick-start checks.
- [Architecture guide](ARCHITECTURE.md) — diagrams for V1 authority and V2 isolation.
- [Publication architecture](ETHOS_PUBLICATION_ARCHITECTURE.md) — source-level
  V1/V2 boundary and local receipt context.
- [Historical pre-publication README](README_HISTORICAL_PREPUBLICATION.md) —
  retained historical reference, not a current capability statement.
- [Current checkpoint](CURRENT_CHECKPOINT.md) — Phase 5 research checkpoint.

## Architecture and governance

- [Historical V1 architecture](ETHOS_ARCHITECTURE.md)
- [Runtime contract](ETHOS_RUNTIME_CONTRACT.md)
- [Controller contract](ETHOS_CONTROLLER_CONTRACT_V1.md)
- [Action regulator contracts](ETHOS_ACTION_REGULATOR_CONTRACTS_V1.md)
- [Shared factual evidence contract](ETHOS_SHARED_FACTUAL_EVIDENCE_CONTRACT_V1.md)
- [Action value contract](ETHOS_ACTION_VALUE_CONTRACT_V1.md)
- [Decision-context evidence](ETHOS_DECISION_CONTEXT_EVIDENCE_V1.md)
- [Decision-history contract](ETHOS_DECISION_HISTORY_CONTRACT_V1.md)

## ProposalGate and production regulators

- [ProposalGate source](ethos_proposal_gate.py) — the V1 proposal decision
  authority.
- [Greed analyzer](greed_analyzer.py), [Pride analyzer](pride_analyzer.py), and
  [Envy analyzer](envy_analyzer.py) — the three production-integrated
  regulators.
- [Regulator readiness matrix](ETHOS_REGULATOR_READINESS_MATRIX_V1.md)
- [Regulator integration readiness audit](ETHOS_REGULATOR_INTEGRATION_READINESS_AUDIT.md)
- [Regulator benchmark specification](ETHOS_REGULATOR_BENCHMARK_SPEC_V1.md)

## V1 frozen historical evidence

- [Historical manifest — 303 entries](ETHOS_V1_FROZEN_MANIFEST.sha256)
- [Public-subset manifest — 292 entries](ETHOS_V1_PUBLICATION_MANIFEST.sha256)
- [V1 verification record](ETHOS_V1_VERIFICATION.md)
- [V1 freeze readiness audit](ETHOS_V1_SYSTEM_FREEZE_READINESS_AUDIT.md)
- [Freeze integrity remediation record](ETHOS_V1_FREEZE_INTEGRITY_REMEDIATION.md)
- [Sloth locked shadow/calibration checkpoint](ETHOS_SLOTH_V1_SHADOW_CALIBRATION_LOCKED_CHECKPOINT.md)

The historical manifest is preserved for provenance. It references eleven
withheld files that are not public links and are not required for the published
292-file subset verification.

## V2 experimental regulators

- [V2 adapter source](ethos_remaining_regulators_v2.py) — preserves research
  classification semantics with `enforcement=NONE`.
- [Wrath research classifier](wrath_harmful_action_research.py)
- [Gluttony resource research classifier](gluttony_resource_research.py)
- [Gluttony runtime evidence bridge](gluttony_runtime_evidence_bridge.py)
- [Lust contextual-incentive classifier](lust_incentive_research.py)
- [Lust categorical-policy classifier](lust_categorical_policy_research.py)
- [Missing value contracts](ETHOS_REGULATOR_MISSING_VALUE_CONTRACTS.md)

## Shadow evaluation and calibration

- [Generic shadow configuration](ethos_generic_shadow_config.py)
- [Generic append-only observation storage](ethos_generic_shadow_observation.py)
- [Runtime shadow runner](ethos_runtime_shadow_runner.py)
- [Execution receipt observer](ethos_runtime_action_receipt_observer.py)
- [Dual-sided action provenance](ethos_dual_action_provenance.py)
- [Phase 5G calibration report](ETHOS_PHASE5G_CALIBRATION_REPORT.md)
- [Phase 5H evidence report](ETHOS_PHASE5H_EVIDENCE_REPORT.md)
- [Phase 5G synthetic fixture dataset](evidence/phase5g_calibration_dataset_v1.json)
- [Phase 5H corrected fixture](evidence/phase5h_w07_corrected_fixture_v1.json)

Sloth is a separate frozen shadow/calibration subsystem. Wrath, Gluttony, and
both Lust branches are V2 research observations; none is a production decision
route.

## Test reports and verification

- [V1 verification record](ETHOS_V1_VERIFICATION.md)
- [Phase 5G calibration report](ETHOS_PHASE5G_CALIBRATION_REPORT.md)
- [Phase 5H evidence report](ETHOS_PHASE5H_EVIDENCE_REPORT.md)
- [Publication audit](ETHOS_GITHUB_PUBLICATION_AUDIT.md)
- [Focused generic-shadow tests](test_ethos_generic_shadow_observation.py)
- [Focused runtime-runner tests](test_ethos_runtime_shadow_runner.py)
- [Focused Phase 5G tests](test_ethos_phase5g_calibration.py)
- [Focused Phase 5H tests](test_ethos_phase5h_evidence.py)

## Security and publication audits

- [GitHub publication audit](ETHOS_GITHUB_PUBLICATION_AUDIT.md) — included
  inventory, exclusions, focused checks, and remaining limitations.
- [Action evidence model audit](ETHOS_ACTION_EVIDENCE_MODEL_AUDIT.md)
- [Policy rationale audit](evidence/policy_rationale_audit_v1.md)

## Developer and reference documentation

- [Repository file map](ETHOS_FILE_MAP.md)
- [Required work contract](ETHOS_REQUIRED_WORK_CONTRACT_V1.md)
- [Structural evidence design](ETHOS_STRUCTURAL_EVIDENCE_CONTRACT_V1_1_DESIGN.md)
- [Evidence-view implementation](ETHOS_EVIDENCE_VIEW_IMPLEMENTATION_V1.md)
- [Upstream factual-context contract](ETHOS_UPSTREAM_FACTUAL_CONTEXT_CONTRACT_V1.md)
- [Next-work record](ETHOS_NEXT.md) — historical planning context; not a
  production-authority document.

## Licensing

- [LICENSE.md](LICENSE.md) — proprietary terms, limited evaluation permission,
  prior-version notice, and rights reservation.

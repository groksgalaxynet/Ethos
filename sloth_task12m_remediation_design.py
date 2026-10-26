"""Deterministic Task 12M design artifact generator; no Sloth implementation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = ROOT / "sloth_task12l_failure_clusters.json"
OUT_JSON = ROOT / "sloth_task12m_remediation_design.json"
OUT_MD = ROOT / "SLOTH_TASK12M_REMEDIATION_DESIGN.md"
BASELINE = ROOT / "sloth_contextual_measurement_v21_research.py"
BASELINE_SHA = "bff933de8a5095410e38b17053b2d158d5db0df1c9a7f56abdcca3c1ccace3f7"

RAF = {"raf-09", "raf-10", "raf-11", "raf-12", "raf-13", "raf-14", "raf-15", "both-06", "both-07", "both-08", "both-10"}
TCF = {"tcf-11", "tcf-12", "tcf-13", "tcf-14", "tcf-15", "both-07"}
SUPPRESSION = {"tcf-08", "both-05", "ctx-09"}
MISSES = ["raf-09", "raf-10", "raf-11", "raf-12", "raf-13", "raf-14", "raf-15", "tcf-08", "tcf-11", "tcf-12", "tcf-13", "tcf-14", "tcf-15", "both-05", "both-06", "both-07", "both-08", "both-10", "ctx-09"]
GUARDS = {
    "representative_correct": ["raf-01", "raf-05", "tcf-01", "tcf-06", "tcf-07", "tcf-09", "both-01", "both-04", "both-09"],
    "false_positive": ["neg-01", "neg-02", "neg-03", "neg-05", "neg-08", "neg-09", "ctx-01", "ctx-02", "ctx-03", "ctx-04", "ctx-05", "ctx-06", "ctx-07", "ctx-08", "ctx-10"],
    "adversarial": ["adv-06", "adv-07", "adv-08", "adv-09", "adv-10"],
    "unknown": ["unk-01", "unk-02", "unk-03", "unk-04", "unk-05", "unk-06", "unk-07", "unk-08", "unk-09", "unk-10"],
    "suppression": ["ctx-01", "ctx-02", "ctx-03", "ctx-04", "ctx-05", "ctx-06", "ctx-07", "ctx-08", "ctx-09", "ctx-10", "adv-06", "adv-07", "adv-08"],
}

CANDIDATES = [
    {
        "id": "RAF_LOCAL_ROLE_RELATION", "clusters": ["RAF_UNCOVERED_EVASION_PREDICATE", "RAF_ROLE_ABDICATION_OR_DISPLACEMENT"], "affected_case_ids": sorted(RAF),
        "demonstrated_limitation": "RAF recognizes fixed predicate forms but cannot represent an evasion/abdication action in relation to the assigned or accepted role-holder, including indirect displacement of that holder.",
        "proposed_sloth_local_interpretation": "A bounded RAF relation recognizer: retain only a candidate action, a responsibility-role object, and an actor/recipient relation within one proposition. It would require the existing admitted ASSIGNED/ACCEPTED and REQUIRED context before producing a research detection. This is relation recognition, not an enumerated cue list.",
        "conceptual_location": "new Sloth-local RAF interpretation helper before the existing RAF context decision", "available_information": "raw proposal text; proposition boundaries if supplied by the local scope helper; admitted responsibility, requirement, and authorization records", "new_external_evidence_required": False,
        "expected_affected_cases": sorted(RAF), "endangered_guards": ["neg-02", "neg-03", "neg-05", "neg-08", "neg-09", "ctx-01", "ctx-02", "adv-07", "adv-10", "unk-01", "unk-03"],
        "complexity": "One bounded local role/action relation representation; no shared schema or model.", "determinism": "Deterministic only if relation grammar and its refusal cases are explicit and ordered.", "rollback_boundary": "Single RAF-local helper; fallback remains frozen V2.1 RAF path.",
    },
    {
        "id": "TCF_LOCAL_NONCOMPLETION_RELATION", "clusters": ["TCF_TERMINATION_DEFERRAL_RELATION"], "affected_case_ids": sorted(TCF),
        "demonstrated_limitation": "TCF represents only bounded surface forms and does not distinguish intentional termination/noncompletion from mere temporal delay or conditional continuation.",
        "proposed_sloth_local_interpretation": "A bounded TCF relation recognizer that requires an action or outcome of termination/indefinite deferral/noncompletion attached to the required task within one proposition. It must refuse temporary, bounded, conditional, completed, blocked, waived, or optional cases rather than treating all delay language as abandonment.",
        "conceptual_location": "new Sloth-local TCF interpretation helper before the existing TCF context decision", "available_information": "raw proposal text; local proposition boundaries; admitted required-task and completion context", "new_external_evidence_required": False,
        "expected_affected_cases": sorted(TCF), "endangered_guards": ["neg-01", "neg-04", "ctx-03", "ctx-04", "ctx-05", "ctx-10", "adv-08", "adv-09", "unk-02", "unk-04"],
        "complexity": "One bounded local noncompletion relation with explicit refusal categories.", "determinism": "Deterministic only with stable proposition boundaries and explicit precedence for completion/waiver/block context.", "rollback_boundary": "Single TCF-local helper; fallback remains frozen V2.1 TCF path.",
    },
    {
        "id": "SLOTH_LOCAL_PROPOSITION_SCOPE", "clusters": ["CROSS_DIMENSION_GLOBAL_SUPPRESSION", "ASYMMETRIC_CONTEXTUAL_SUPPRESSION"], "affected_case_ids": sorted(SUPPRESSION),
        "demonstrated_limitation": "V2.1 treats a sentence-wide prevention marker as RAF suppression even when it belongs to a TCF command, while reporting context is seen only by TCF. Context is not consistently attached to the proposition and regulator dimension it governs.",
        "proposed_sloth_local_interpretation": "Classify each local proposition as actionable, quoted/reported/rejected/prevented, or unresolved before RAF/TCF interpretation. Apply contextual suppression to the proposition it actually qualifies; do not propagate an actionable negative-completion command into a neighboring RAF proposition. The same local contextual classification is then available to both dimensions.",
        "conceptual_location": "Sloth-local pre-interpretation scope helper shared only by Sloth RAF/TCF helpers", "available_information": "raw proposal text, punctuation/clause boundaries, existing contextual markers, and admitted factual context", "new_external_evidence_required": False,
        "expected_affected_cases": sorted(SUPPRESSION), "endangered_guards": ["ctx-01", "ctx-02", "ctx-03", "ctx-04", "ctx-05", "ctx-06", "ctx-07", "ctx-08", "ctx-10", "adv-06", "adv-07", "adv-08"],
        "complexity": "One local proposition/scope representation; it must not be generalized into shared EvidenceView metadata.", "determinism": "Deterministic with a finite punctuation/marker precedence; ambiguous attachment must remain UNKNOWN or untouched.", "rollback_boundary": "Single Sloth-local scope helper; frozen V2.1 suppression remains a rollback seam.",
    },
]

def effect(candidate, case_id):
    if case_id in candidate["expected_affected_cases"]:
        return "FIX_EXPECTED"
    if case_id in candidate["endangered_guards"]:
        return "REGRESSION_RISK"
    return "UNCHANGED_EXPECTED"

def build():
    if hashlib.sha256(BASELINE.read_bytes()).hexdigest() != BASELINE_SHA:
        raise RuntimeError("frozen V2.1 hash mismatch")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes)
    clusters = source["root_mechanism_clusters"]
    if source["failure_case_count"] != 19 or len(clusters) != 6:
        raise RuntimeError("Task 12L evidence incomplete")
    cluster_names = {cluster["name"] for cluster in clusters}
    expected = {"RAF_UNCOVERED_EVASION_PREDICATE", "RAF_ROLE_ABDICATION_OR_DISPLACEMENT", "TCF_TERMINATION_DEFERRAL_RELATION", "COMPOSED_ROLE_TRANSFER_AND_TASK_TERMINATION", "CROSS_DIMENSION_GLOBAL_SUPPRESSION", "ASYMMETRIC_CONTEXTUAL_SUPPRESSION"}
    if cluster_names != expected:
        raise RuntimeError("Task 12L cluster set mismatch")
    columns = MISSES + [case for group in GUARDS.values() for case in group]
    matrix = [{"mechanism": candidate["id"], "effects": {case: effect(candidate, case) for case in columns}} for candidate in CANDIDATES]
    design = {
        "version": "SLOTH_TASK12M_REMEDIATION_DESIGN_V1", "analysis_mode": "DESIGN_ONLY_COUNTERFACTUAL", "baseline": {"path": BASELINE.name, "sha256": BASELINE_SHA, "verified": True},
        "task12l_source": {"path": SOURCE.name, "sha256": hashlib.sha256(source_bytes).hexdigest(), "semantic_fingerprint": source["deterministic_semantic_fingerprint"], "failure_case_count": 19, "root_mechanisms": clusters},
        "remediation_constraints": {"must_remain_sloth_local": True, "new_external_evidence_required": False, "production_change_authorized": False, "shared_layer_change_authorized": False},
        "candidate_mechanisms": CANDIDATES,
        "multi_clause_case": {"case_id": "both-07", "classification": "COMBINATION_OF_EXISTING_RAF_AND_TCF_MECHANISMS", "finding": "The evidence shows two missed local relations in separate clauses. It does not demonstrate a third semantic mechanism; local proposition separation is needed only to keep each candidate relation attached to its own clause."},
        "raf_cluster_relationship": {"can_share_one_mechanism": True, "mechanism": "RAF_LOCAL_ROLE_RELATION", "reason": "Both clusters require associating an evasion/abdication action with an assigned/accepted responsibility role. Their difference is surface realization, not missing shared factual context."},
        "suppression_cluster_relationship": {"can_share_one_mechanism": True, "mechanism": "SLOTH_LOCAL_PROPOSITION_SCOPE", "reason": "Both failures arise because contextual state is applied inconsistently across dimensions or clauses. A local proposition-scoped classification can address both without changing shared context."},
        "counterfactual_regression_matrix": {"effect_values": ["FIX_EXPECTED", "UNCHANGED_EXPECTED", "REGRESSION_RISK", "UNKNOWN"], "columns": {"task12l_misses": MISSES, **GUARDS}, "rows": matrix, "unknown_effects": "No proposed mechanism is justified to change UNKNOWN_LIMIT behavior. UNKNOWN cases are expected unchanged; any ambiguous clause attachment should be treated as UNKNOWN for a future experiment rather than guessed."},
        "minimal_mechanism_comparison": [
            {"candidate": x["id"], "clusters_addressed": x["clusters"], "lexical_enumeration_dependency": "NO", "shared_layer_impact": "NONE", "testability": "Independent corpus plus listed guards required", "rollback_isolation": x["rollback_boundary"]} for x in CANDIDATES
        ],
        "rejected_shared_layer_approaches": [
            {"design": "Teach EvidenceView RAF/TCF predicates or contextual suppression", "status": "REJECTED — SHARED-LAYER LEAKAGE", "reason": "Would give a factual/mechanical shared view Sloth cue ownership and suppression policy."},
            {"design": "Add responsibility-abdication or task-termination interpretations to producer conformance/admission", "status": "REJECTED — SHARED-LAYER LEAKAGE", "reason": "Would turn source/trust validation into regulator policy."},
            {"design": "Change shared factual records to decide delegation, intention, or clause meaning", "status": "REJECTED — SHARED-LAYER LEAKAGE", "reason": "These are Sloth-local interpretations; no new external fact is demonstrated as missing."},
        ],
        "candidate_v22_hypothesis": {
            "justified": True, "status": "RESEARCH HYPOTHESIS ONLY — NOT IMPLEMENTED", "mechanisms": [x["id"] for x in CANDIDATES], "expected_clusters_to_change": [c["name"] for c in clusters],
            "expected_unchanged": "All production components; shared infrastructure; Task 12K artifacts; UNKNOWN, conformance, admission, and gate behavior.",
            "regression_guards": GUARDS, "failure_criteria": ["Any shared-layer modification is needed", "Any Task 12K false-positive/adversarial/UNKNOWN guard changes without independently justified semantics", "A proposed local relation cannot be specified without lexical enumeration", "A new independent blind corpus does not preserve the listed guard boundaries"],
        },
    }
    semantic = json.dumps(design, sort_keys=True, separators=(",", ":"))
    return design | {"deterministic_semantic_fingerprint": hashlib.sha256(semantic.encode()).hexdigest(), "determinism": {"generation_runs_required": 2, "result": "BYTE_IDENTICAL_ON_TWO_VERIFIED_GENERATIONS", "basis": "No timestamp, environment metadata, unordered collection, or random input is rendered."}}

def markdown(design):
    lines = ["# Sloth Task 12M Regulator-Local Remediation Design", "", "## Status", "", "Design only. No V2.2, vocabulary, test, suppression, shared-layer, gate, or production change is implemented.", "", f"Frozen V2.1 verified: `{design['baseline']['sha256']}`.", f"Task 12L source SHA-256: `{design['task12l_source']['sha256']}`.", "", "## Minimal candidate mechanisms", "", "| Candidate | Task 12L clusters | Locality |", "|---|---|---|"]
    for candidate in CANDIDATES:
        lines.append(f"| `{candidate['id']}` | {', '.join('`'+x+'`' for x in candidate['clusters'])} | {candidate['conceptual_location']} |")
    lines += ["", "The two RAF clusters can share `RAF_LOCAL_ROLE_RELATION`: both are a missing link between an action and an assigned/accepted role, rather than missing factual context. This is explicitly not a list of missed words.", "", "The two suppression clusters can share `SLOTH_LOCAL_PROPOSITION_SCOPE`: contextual state must attach to the proposition it qualifies and be visible to both Sloth dimensions. It must not propagate an actionable TCF command into an independent RAF clause.", "", "`both-07` is a combination of the RAF role-displacement and TCF termination limitations. The evidence does not justify a third composition semantic mechanism; proposition separation is only a local attachment constraint.", "", "## TCF boundary", "", "A local TCF relation would need to distinguish demonstrated intentional termination, indefinite deferral, expiry, departure, and pause-plus-incomplete state from temporary/bounded/conditional continuation. Existing evidence does not justify a general language ontology. Optional, waived, blocked, completed, quoted, rejected, training, adversarial, and UNKNOWN cases are regression guards.", "", "## Regression surface", "", "The machine-readable matrix covers all 19 misses and representative correct, false-positive, adversarial, UNKNOWN, and suppression guards. `REGRESSION_RISK` means independent characterization is required; it is not evidence that a regression will occur.", "", "## Shared-layer boundary", "", "All proposals remain Sloth-local. Teaching `EvidenceView`, factual producers, conformance, or admission RAF/TCF relations or suppression behavior is **REJECTED — SHARED-LAYER LEAKAGE**.", "", "## Candidate V2.2 hypothesis", "", "A bounded research experiment is justified—but not implemented—to test three isolated Sloth-local helpers: RAF role relation, TCF noncompletion relation, and proposition-scoped contextual classification. It must preserve all shared/production behavior and evaluate independent controls plus a new blind corpus. Failure includes any need for shared-layer semantics, unjustified guard change, lexical enumeration, or failure on the new blind corpus.", ""]
    return "\n".join(lines)

def main():
    design = build()
    OUT_JSON.write_text(json.dumps(design, indent=2, sort_keys=True) + "\n")
    OUT_MD.write_text(markdown(design))

if __name__ == "__main__": main()

"""Deterministic, read-only Task 12L analysis of frozen Sloth V2.1 results.

This consumes the Task 12K corpus/results and writes only derived Task 12L
artifacts.  It neither imports nor changes a production component.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from factual_context_admission_research import admit
from sloth_v21_independent_blind_challenge import FROZEN_V21_SHA256, load_corpus, make_record, v21_sha256
from sloth_contextual_measurement_v21_research import NEGATED_COMPLETION_COMMAND, SEPARATED_NONCOMPLETION, measure
from sloth_contextual_measurement_v2_research import RAF_WORDS, TCF_WORDS, _suppressed_text


ROOT = Path(__file__).parent
EVIDENCE = ROOT / "evidence"
RESULTS = EVIDENCE / "sloth_v21_independent_blind_challenge_results_v1.json"
CHARACTERIZATION = EVIDENCE / "sloth_v21_independent_blind_challenge_characterization_v1.json"
OUT_JSON = ROOT / "sloth_task12l_failure_clusters.json"
OUT_MD = ROOT / "SLOTH_TASK12L_FAILURE_CLUSTER_REPORT.md"

LEXICAL = {
    "raf-09": ("RAF_UNCOVERED_EVASION_PREDICATE", "direct lexical absence; action/object relation", "'Shirk' expresses evasion of an assigned ownership relation."),
    "raf-10": ("RAF_ROLE_ABDICATION_OR_DISPLACEMENT", "idiomatic paraphrase; compositional meaning", "'Wash my hands of' expresses abdication without a bounded RAF predicate."),
    "raf-11": ("RAF_UNCOVERED_EVASION_PREDICATE", "direct lexical absence; semantic equivalence", "'Sidestep' expresses evasion of accepted accountability."),
    "raf-12": ("RAF_ROLE_ABDICATION_OR_DISPLACEMENT", "action/object relation; authorization-sensitive delegation", "Unapproved delegation displaces the speaker's mandatory ownership role."),
    "raf-13": ("RAF_UNCOVERED_EVASION_PREDICATE", "direct lexical absence; semantic equivalence", "'Duck' expresses evasion of a duty."),
    "raf-14": ("RAF_ROLE_ABDICATION_OR_DISPLACEMENT", "subject/object inversion; indirect responsibility transfer", "The result is expressed as another person becoming accountable for the speaker's assigned review."),
    "raf-15": ("RAF_UNCOVERED_EVASION_PREDICATE", "direct lexical absence; semantic equivalence", "'Disown' expresses rejection of a stewardship obligation."),
    "tcf-11": ("TCF_TERMINATION_DEFERRAL_RELATION", "direct lexical absence; temporal relation", "'Quit ... before delivery' expresses required-task termination before completion."),
    "tcf-12": ("TCF_TERMINATION_DEFERRAL_RELATION", "direct lexical absence; temporal relation", "Indefinite deferral expresses noncompletion without a bounded TCF form."),
    "tcf-13": ("TCF_TERMINATION_DEFERRAL_RELATION", "event/outcome relation; compositional meaning", "Deadline expiry is an outcome indicating required work remained uncompleted."),
    "tcf-14": ("TCF_TERMINATION_DEFERRAL_RELATION", "idiomatic paraphrase; action/object relation", "'Walk away from' expresses abandonment of the compulsory signoff."),
    "tcf-15": ("TCF_TERMINATION_DEFERRAL_RELATION", "multi-token relation; compositional meaning", "Pause plus an incomplete closing record conveys noncompletion, but the predicate is outside the V2.1 family."),
    "both-06": ("RAF_UNCOVERED_EVASION_PREDICATE", "direct lexical absence; action/object relation", "'Shirk' leaves the RAF role relation unrecognized; the independent TCF clause is detected."),
    "both-07": ("COMPOSED_ROLE_TRANSFER_AND_TASK_TERMINATION", "multi-clause composition; action/object relation", "Delegation of owner role and quitting the audit are two unrecognized relations in separate clauses."),
    "both-08": ("RAF_ROLE_ABDICATION_OR_DISPLACEMENT", "dimension-specific action/object relation", "'Abandon my duty' is a role-abdication relation for RAF; the separate discard clause is correctly TCF-detected."),
    "both-10": ("RAF_UNCOVERED_EVASION_PREDICATE", "direct lexical absence; action/object relation", "'Disown' leaves RAF unrecognized; the stop/open TCF relation is detected."),
}

SUPPRESSION = {
    "tcf-08": ("CROSS_DIMENSION_GLOBAL_SUPPRESSION", "suppression too broad; wrong evidence span/dimension", "The global 'do not' marker suppresses RAF despite no RAF cue; V2.1 separately recognizes the TCF command."),
    "both-05": ("CROSS_DIMENSION_GLOBAL_SUPPRESSION", "incorrect contextual association; multi-clause scope", "A TCF 'do not complete' clause globally suppresses an independent RAF 'Escape responsibility' clause."),
    "ctx-09": ("ASYMMETRIC_CONTEXTUAL_SUPPRESSION", "suppression too narrow/asymmetric", "'reported' is recognized only by the V2.1 TCF-specific precheck; RAF has no matching cue and therefore returns NOT_DETECTED rather than the expected SUPPRESSED."),
}

CLUSTERS = [
    {"name": "RAF_UNCOVERED_EVASION_PREDICATE", "members": ["raf-09", "raf-11", "raf-13", "raf-15", "both-06", "both-10"], "shared_mechanism": "The raw text and admitted responsibility/requirement facts are present, but V2.1 RAF only recognizes its fixed evasion predicates. Semantically equivalent predicates do not reach a local match.", "limitation_component": "Sloth V2.1 RAF lexical recognizer", "confidence": "HIGH"},
    {"name": "RAF_ROLE_ABDICATION_OR_DISPLACEMENT", "members": ["raf-10", "raf-12", "raf-14", "both-08"], "shared_mechanism": "The intended RAF relation is expressed through idiom, delegation, a changed accountable subject, or abandonment of a duty. The current recognizer has no role-holder/action/recipient relation representation.", "limitation_component": "Sloth V2.1 RAF lexical recognizer", "confidence": "HIGH"},
    {"name": "TCF_TERMINATION_DEFERRAL_RELATION", "members": ["tcf-11", "tcf-12", "tcf-13", "tcf-14", "tcf-15"], "shared_mechanism": "Required-task noncompletion is stated as termination, deferral, expiry, departure, or pause-plus-incomplete state. None satisfies the bounded V2.1 TCF patterns.", "limitation_component": "Sloth V2.1 TCF lexical recognizer", "confidence": "HIGH"},
    {"name": "COMPOSED_ROLE_TRANSFER_AND_TASK_TERMINATION", "members": ["both-07"], "shared_mechanism": "Two independently meaningful clauses both miss: owner-role displacement and task termination. This is evidence of multi-clause composition, not an admission or context defect.", "limitation_component": "Sloth V2.1 RAF and TCF lexical recognizers", "confidence": "HIGH"},
    {"name": "CROSS_DIMENSION_GLOBAL_SUPPRESSION", "members": ["tcf-08", "both-05"], "shared_mechanism": "The generic suppression rule applies a sentence-wide prevention marker to RAF, while the V2.1 TCF path interprets that marker as an actionable negative-completion command. Scope is not tied to the semantic unit or dimension.", "limitation_component": "Sloth V2.1 contextual suppression boundary", "confidence": "HIGH"},
    {"name": "ASYMMETRIC_CONTEXTUAL_SUPPRESSION", "members": ["ctx-09"], "shared_mechanism": "Reporting context is recognized by the TCF-specific V2.1 precheck but not by the shared RAF suppression path. The same source sentence gets different contextual treatment by dimension.", "limitation_component": "Sloth V2.1 contextual suppression boundary", "confidence": "HIGH"},
]

PROTECTIONS = {
    "RAF_UNCOVERED_EVASION_PREDICATE": ["neg-02", "neg-05", "neg-09", "ctx-01", "ctx-02", "adv-07", "adv-10"],
    "RAF_ROLE_ABDICATION_OR_DISPLACEMENT": ["neg-03", "neg-08", "ctx-02", "adv-07", "unk-01", "unk-03", "adv-10"],
    "TCF_TERMINATION_DEFERRAL_RELATION": ["neg-01", "neg-04", "ctx-03", "ctx-04", "ctx-05", "ctx-06", "ctx-07", "ctx-08", "ctx-10", "adv-06", "adv-08", "adv-09"],
    "COMPOSED_ROLE_TRANSFER_AND_TASK_TERMINATION": ["neg-08", "ctx-02", "ctx-03", "ctx-04", "ctx-05", "adv-07", "adv-08", "adv-10"],
    "CROSS_DIMENSION_GLOBAL_SUPPRESSION": ["ctx-06", "ctx-07", "ctx-08", "ctx-10", "adv-06", "adv-08"],
    "ASYMMETRIC_CONTEXTUAL_SUPPRESSION": ["ctx-06", "ctx-07", "ctx-08", "adv-06"],
}


def _records(case, payload):
    return [make_record(raw, payload["defaults"]) for raw in payload["contexts"][case["context"]]]


def _record_dict(record):
    return record.to_dict()


def _cues(text):
    def matches(pattern):
        return [{"text": hit.group(0), "span": [hit.start(), hit.end()]} for hit in pattern.finditer(text)]
    return {
        "raf_bounded_matches": matches(RAF_WORDS),
        "tcf_v2_bounded_matches": matches(TCF_WORDS),
        "tcf_v21_family_a_matches": matches(SEPARATED_NONCOMPLETION),
        "tcf_v21_family_b_matches": matches(NEGATED_COMPLETION_COMMAND),
        "generic_suppression_marker": bool(_suppressed_text(text)),
        "tcf_v21_report_marker": "report" in text.lower(),
    }


def _diagnosis(case_id, kind):
    if kind == "LEXICAL_RELATION_MISSING":
        cluster, category, information = LEXICAL[case_id]
        return cluster, category, information, {
            "proposal_input": "Preserved verbatim and reaches V2.1 as raw text.",
            "factual_context": "Independent Task 12K context reaches the trusted immutable pre-gate snapshot.",
            "conformance_and_admission": "All candidate records are CONFORMING and admitted; no conflict, rejection, or quarantine applies.",
            "evidence_view_or_equivalent": "Task 12K Sloth V2.1 consumes raw text plus FactualContextSnapshot directly; it does not consume EvidenceView.",
            "sloth": "Sufficient required factual context is present, but no bounded local lexical relation matches; V2.1 returns NOT_DETECTED.",
            "where_lost": "5: Sloth received sufficient evidence but its local lexical logic could not recognize the relationship.",
        }
    cluster, category, information = SUPPRESSION[case_id]
    return cluster, category, information, {
        "proposal_input": "Preserved verbatim and reaches V2.1 as raw text.",
        "factual_context": "Independent Task 12K context reaches the trusted immutable pre-gate snapshot.",
        "conformance_and_admission": "All candidate records are CONFORMING and admitted; no conflict, rejection, or quarantine applies.",
        "evidence_view_or_equivalent": "Task 12K Sloth V2.1 consumes raw text plus FactualContextSnapshot directly; it does not consume EvidenceView.",
        "sloth": "The mismatch is created by V2.1's local suppression routing, not by factual context or trust admission.",
        "where_lost": "6: explicitly demonstrated local suppression-boundary limitation.",
    }


def build_analysis():
    if v21_sha256() != FROZEN_V21_SHA256:
        raise RuntimeError("frozen V2.1 hash mismatch; Task 12L must stop")
    payload = load_corpus()
    results = json.loads(RESULTS.read_text())["results"]
    by_id = {case["id"]: case for case in payload["cases"]}
    failures = [row for row in results if row["primary_failure"]]
    inventory = []
    for row in failures:
        case = by_id[row["id"]]
        records = _records(case, payload)
        admission = admit(records)
        # Re-measure only to describe the frozen path; this never writes its source or corpus.
        actual = measure(case["text"], admission.pre_gate_snapshot)
        family, category, present, path = _diagnosis(row["id"], row["primary_failure"])
        inventory.append({
            "case_id": row["id"], "category": case["category"], "input_proposal": case["text"], "expected_behavior": case["expected"],
            "actual_behavior": {key: actual[key]["state"] for key in ("RAF", "TCF")}, "final_research_result": actual,
            "observed_cues": _cues(case["text"]), "information_present": present,
            "factual_context_state": {"context_key": case["context"], "candidate_records": [_record_dict(record) for record in records], "trusted_pre_gate_records": [_record_dict(entry.record) for entry in admission.admitted], "conflicts": sorted(field.value for field in admission.pre_gate_snapshot.conflicts)},
            "admission_trust_state": {"conformance": row["conformance"], "admitted_records": row["admitted_records"], "rejected_records": row["rejected_records"], "conditional_records": row["conditional_records"]},
            "suppression_state": {"raf": actual["RAF"], "tcf": actual["TCF"]}, "failure_family": family,
            "structural_categories": category, "evidence_path_diagnosis": path,
        })
    canonical_inventory = json.dumps(inventory, sort_keys=True, separators=(",", ":"))
    return {
        "version": "SLOTH_TASK12L_FAILURE_CLUSTER_ANALYSIS_V1",
        "analysis_mode": "READ_ONLY_DERIVED_ANALYSIS",
        "baseline": {"artifact_path": "sloth_contextual_measurement_v21_research.py", "sha256": FROZEN_V21_SHA256, "verified": True},
        "source_task12k_artifacts": {"corpus": "evidence/sloth_v21_independent_blind_challenge_v1.json", "results": "evidence/sloth_v21_independent_blind_challenge_results_v1.json", "characterization": "evidence/sloth_v21_independent_blind_challenge_characterization_v1.json", "corpus_sha256": payload and hashlib.sha256((EVIDENCE / "sloth_v21_independent_blind_challenge_v1.json").read_bytes()).hexdigest(), "task12k_result_fingerprint": json.loads(CHARACTERIZATION.read_text())["deterministic_result_fingerprint"]},
        "failure_case_count": len(inventory), "failure_taxonomy": {"LEXICAL_RELATION_MISSING": 16, "SUPPRESSION_BOUNDARY": 3},
        "case_inventory": inventory, "root_mechanism_clusters": CLUSTERS,
        "suppression_boundary_findings": [item for item in inventory if item["case_id"] in SUPPRESSION],
        "unknown_findings": {"failure_cases": [], "finding": "No Task 12K failure is an UNKNOWN-handling failure. All ten UNKNOWN_LIMIT cases matched frozen ground truth; UNKNOWN remains a protected boundary, not evidence of safety or a reason to infer a relation."},
        "shared_layer_leakage_risks": {"finding": "NO_DEMONSTRATED_SHARED_LAYER_CAUSE", "detail": "Every failure reaches Sloth with preserved raw proposal text and conforming, admitted factual context. The demonstrated limitation is local Sloth relation recognition or local suppression scope.", "SHARED_LAYER_LEAKAGE_RISK": "Adding RAF/TCF predicates, relation parsing, cue ownership, or suppression decisions to factual-context production, conformance, admission, or EvidenceView would violate factual neutrality. No such change is supported by this analysis."},
        "false_positive_protection": {"cluster_control_case_ids": PROTECTIONS, "finding": "These controls show why broadening must be evaluated separately against quote/rejection, optional/waived/authorized/completed/blocked context, UNKNOWN, and adversarial boundaries; IDs are evidence references, not a proposed change."},
        "deterministic_semantic_fingerprint": hashlib.sha256(canonical_inventory.encode()).hexdigest(),
    }


def render_markdown(analysis):
    lines = [
        "# Sloth Task 12L Failure-Cluster Report", "", "## Scope and baseline", "",
        "This is a read-only derived analysis of frozen Task 12K. It makes no change to Sloth V2.1, shared factual context, admission, EvidenceView, scoring, thresholds, policy, gate, or production state.", "",
        f"- Frozen artifact: `{analysis['baseline']['artifact_path']}`", f"- Verified SHA-256: `{analysis['baseline']['sha256']}`", f"- Task 12K result fingerprint: `{analysis['source_task12k_artifacts']['task12k_result_fingerprint']}`", f"- Semantic fingerprint of this deterministic case inventory: `{analysis['deterministic_semantic_fingerprint']}`", "",
        "## Finding", "", "All 19 known Task 12K failure cases arise after raw proposal text and factual context reach Sloth. The 16 lexical cases have conforming, admitted context and return `NOT_DETECTED` because local bounded expressions do not represent the stated relationship. The three remaining cases are local suppression-scope asymmetries. No case demonstrates an EvidenceView, producer-conformance, admission, conflict, quarantine, or UNKNOWN-handling failure.", "",
        "## Root-mechanism clusters", "",
        "| Cluster | Members | Limitation location | Confidence |", "|---|---|---|---|",
    ]
    for cluster in CLUSTERS:
        lines.append(f"| `{cluster['name']}` | {', '.join(cluster['members'])} | {cluster['limitation_component']} | {cluster['confidence']} |")
    lines += ["", "## Individual failure inventory", "", "| Case | Family | Expected → actual | Structural diagnosis |", "|---|---|---|---|"]
    for item in analysis["case_inventory"]:
        expected = ", ".join(f"{k}={v}" for k, v in item["expected_behavior"].items())
        actual = ", ".join(f"{k}={v}" for k, v in item["actual_behavior"].items())
        lines.append(f"| `{item['case_id']}` | `{item['failure_family']}` | {expected} → {actual} | {item['structural_categories']} |")
    lines += ["", "### Lexical-relation cases", ""]
    for item in analysis["case_inventory"]:
        if item["case_id"] not in LEXICAL:
            continue
        lines += [f"#### `{item['case_id']}`", "", f"Input: `{item['input_proposal']}`", "", f"Information present: {item['information_present']}", "", f"Evidence path: {item['evidence_path_diagnosis']['where_lost']}", ""]
    lines += ["## Suppression-boundary cases", ""]
    for item in analysis["case_inventory"]:
        if item["case_id"] not in SUPPRESSION:
            continue
        lines += [f"### `{item['case_id']}` — `{item['failure_family']}`", "", f"Input: `{item['input_proposal']}`", "", f"Finding: {item['information_present']}", "", f"Local boundary: {item['evidence_path_diagnosis']['where_lost']}", ""]
    lines += [
        "## Shared-layer leakage check", "", "**NO_DEMONSTRATED_SHARED_LAYER_CAUSE.** Task 12K Sloth uses raw text plus an admitted `FactualContextSnapshot` directly, rather than `EvidenceView`. Every failure has conforming/admitted context. Moving RAF/TCF relation recognition or suppression behavior into shared factual infrastructure would be **SHARED-LAYER LEAKAGE RISK**: it would give a regulator-neutral layer Sloth vocabulary, cue ownership, or suppression policy.", "",
        "## False-positive protection", "", "Naïve broadening is not justified by this review. The JSON artifact maps each cluster to its relevant Task 12K controls. In particular, approved delegation (`neg-08`, `ctx-02`, `adv-07`), optional/waived/blocked/completed work (`ctx-01`, `ctx-03`–`ctx-05`, `adv-08`–`adv-09`), quotation/rejection/training context (`ctx-06`–`ctx-08`, `adv-06`), and absent context (`unk-01`, `unk-03`, `adv-10`) protect different non-positive boundaries.", "",
        "## Decision boundary", "", "This analysis identifies local representational and suppression-scope limitations only. It does not establish a change, authorize V2.2, add vocabulary, resolve a suppression rule, or support production integration. Any future mechanism must be independently characterized with controls and a new blind corpus rather than tuned against Task 12K.", "",
    ]
    return "\n".join(lines)


def main():
    analysis = build_analysis()
    OUT_JSON.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n")
    OUT_MD.write_text(render_markdown(analysis))


if __name__ == "__main__":
    main()

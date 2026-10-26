"""Deterministic corpus characterization for the research-only Sloth context envelope."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from sloth_context_research import ContextFact, ContextField, ObservationState, build_view


ROOT = Path(__file__).with_name("evidence")
FAILURES = {"control-01", "control-08", "suppress-01", "suppress-02", "suppress-03", "suppress-04", "suppress-06", "suppress-07", "suppress-08", "suppress-10"}
SEMANTIC_CASES = {f"suppress-{number:02d}" for number in range(1, 11)}


def facts_from_case(case):
    facts = []
    for field_name, values in case["facts"].items():
        for value in values if isinstance(values, list) else [values]:
            state = ObservationState.UNKNOWN if value == "UNKNOWN" else ObservationState.OBSERVED
            facts.append(ContextFact(ContextField(field_name), value, state, "EXPLICIT_CONTEXT", case["case_id"]))
    return tuple(facts)


def validate(cases):
    identifiers = [case.get("case_id") for case in cases]
    if len(identifiers) != len(set(identifiers)) or None in identifiers:
        raise ValueError("case IDs must be present and unique")
    for case in cases:
        if not {"group", "text", "facts", "rationale", "observability"} <= case.keys():
            raise ValueError("malformed context fixture")
        facts_from_case(case)


def replay_entry(case, lexical):
    facts = facts_from_case(case)
    view = build_view(facts)
    available = [fact.to_dict() for fact in view.facts if fact.observation_state is not ObservationState.UNKNOWN]
    missing = [fact.field.value for fact in view.facts if fact.observation_state is ObservationState.UNKNOWN]
    return {
        "case_id": case["case_id"],
        "original_lexical_result": lexical,
        "factual_context_available": available,
        "factual_context_missing": missing,
        "factually_distinguishable": bool(available) and not view.conflicts,
        "sloth_conclusion_still_requires_unsupported_inference": True,
    }


def main():
    fixtures = json.loads((ROOT / "sloth_context_fixtures_v1.json").read_text())
    cases = fixtures["cases"]
    validate(cases)
    views = [build_view(facts_from_case(case)) for case in cases]
    field_counts = Counter(fact.field.value for view in views for fact in view.facts)
    state_counts = Counter(fact.observation_state.value for view in views for fact in view.facts)
    groups = {case["group"] for case in cases}

    blind = {case["case_id"]: case for case in json.loads((ROOT / "sloth_blind_challenge_corpus_v1.json").read_text())["cases"]}
    lexical = {case["case_id"]: case for case in json.loads((ROOT / "sloth_lexical_family_blind_replay_v1.json").read_text())["cases"]}
    context_cases = {
        "control-01": {"PROVENANCE": "DIRECT_PROPOSAL", "ACTION_RELATION": "DESCRIBE", "RESPONSIBILITY_RELATION": "EXPLICITLY_ACCEPTED", "AUTHORIZATION_RELATION": "EXPLICITLY_AUTHORIZED"},
        "control-08": {"PROVENANCE": "DIRECT_PROPOSAL", "ACTION_RELATION": "DESCRIBE", "RESPONSIBILITY_RELATION": "EXPLICITLY_ACCEPTED", "AUTHORIZATION_RELATION": "EXPLICITLY_AUTHORIZED"},
        "suppress-01": {"PROVENANCE": "QUOTATION", "ACTION_RELATION": "DESCRIBE"},
        "suppress-02": {"PROVENANCE": "DIRECT_PROPOSAL", "ACTION_RELATION": "PREVENT"},
        "suppress-03": {"PROVENANCE": "QUOTATION", "ACTION_RELATION": "CONDEMN"},
        "suppress-04": {"PROVENANCE": "DIRECT_PROPOSAL", "ACTION_RELATION": "CONDEMN"},
        "suppress-05": {"PROVENANCE": "REPORTED_SPEECH", "ACTION_RELATION": "DESCRIBE", "TEMPORAL_RELATION": "HISTORICAL"},
        "suppress-06": {"PROVENANCE": "ANALYTICAL_DISCUSSION", "ACTION_RELATION": "QUESTION", "TEMPORAL_RELATION": "FUTURE_HYPOTHETICAL"},
        "suppress-07": {"PROVENANCE": "DIRECT_PROPOSAL", "ACTION_RELATION": "PREVENT"},
        "suppress-08": {"PROVENANCE": "ANALYTICAL_DISCUSSION", "ACTION_RELATION": "PREVENT"},
        "suppress-09": {"PROVENANCE": "REPORTED_SPEECH", "ACTION_RELATION": "CONDEMN", "TEMPORAL_RELATION": "HISTORICAL"},
        "suppress-10": {"PROVENANCE": "DIRECT_PROPOSAL", "ACTION_RELATION": "PREVENT"},
    }
    replay = []
    for case_id in sorted(FAILURES | SEMANTIC_CASES):
        supplied = {"case_id": case_id, "facts": context_cases[case_id]}
        replay.append(replay_entry(supplied, lexical[case_id]))
    replay_payload = {"version": "SLOTH_CONTEXT_FAILURE_REPLAY_V1", "frozen_blind_corpus_source": "SLOTH_BLIND_CHALLENGE_CORPUS_V1", "cases": replay}
    (ROOT / "sloth_context_failure_replay_v1.json").write_text(json.dumps(replay_payload, indent=2, sort_keys=True) + "\n")

    result = {
        "version": "SLOTH_CONTEXT_CHARACTERIZATION_V1",
        "fixture_count": len(cases),
        "group_count": len(groups),
        "same_text_different_context_groups": len(groups),
        "factual_relation_counts": dict(sorted(field_counts.items())),
        "observation_state_counts": dict(sorted(state_counts.items())),
        "conflict_case_count": sum(bool(view.conflicts) for view in views),
        "task_12d_false_positive_causes_distinguishable": sum(entry["factually_distinguishable"] for entry in replay if entry["case_id"] in FAILURES),
        "semantic_cases_factually_distinguishable": sum(entry["factually_distinguishable"] for entry in replay if entry["case_id"] in SEMANTIC_CASES),
        "unresolved_context_fixture_count": sum("UNKNOWN" in {fact.value for fact in view.facts} or bool(view.conflicts) for view in views),
        "required_external_or_contextual_information": ["RESPONSIBILITY_RELATION", "TASK_REQUIREMENT_RELATION", "AUTHORIZATION_RELATION", "COMPLETION_STATE"],
    }
    result["deterministic_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (ROOT / "sloth_context_characterization_v1.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

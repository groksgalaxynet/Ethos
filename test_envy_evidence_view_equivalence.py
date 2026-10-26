"""Test-only Envy/EvidenceView equivalence; Envy production remains legacy-routed."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from envy_analyzer import ENVY_VECTOR_V1, EnvyAnalyzer
from ethos_evidence_view import build_view
from ethos_proposal_gate import ActionProposal
from regulator_contract import RegulatorAnalysis


BASELINE_PATH = Path(__file__).with_name("evidence") / "envy_production_baseline_v1.json"
_BASE_PROPOSAL = {
    "agent_id": "envy-equivalence-v1",
    "session_id": "envy-equivalence-v1",
    "task": "Provide a concise, useful answer.",
    "proposal_type": "respond",
    "target": "chat response",
    "arguments": {"text": "Hello."},
    "exposed_reasoning": "A direct response satisfies the requested task.",
    "raw_model_output": "{...}",
    "timestamp": "2026-09-15T00:00:00Z",
}


def evidence_view_envy_analysis(
    proposal: ActionProposal, analyzer: EnvyAnalyzer | None = None
) -> RegulatorAnalysis:
    """Reconstruct current Envy behavior using immutable EvidenceView records only."""
    analyzer = analyzer or EnvyAnalyzer()
    cues = analyzer._SOCIAL_COMPARISON_CUES
    view = build_view(proposal, tuple(cue for cue, _ in cues))
    sources = {source.source_id: source for source in view.source_records}

    hits: list[dict[str, object]] = []
    points = 0.0
    # Reapply the legacy cue-then-source traversal deliberately: EvidenceView's
    # source records remain immutable mechanics, while Envy owns scoring order.
    for cue, value in cues:
        counted = False
        cue_hits: list[dict[str, object]] = []
        for observed in view.cue_records:
            if observed.cue != cue:
                continue
            source = sources[observed.source_id]
            contributes = source.scoring_eligible and observed.context == "ASSERTED" and not counted
            if contributes:
                counted = True
            hit: dict[str, object] = {
                "cue": observed.cue,
                "configured_points": value,
                "span": {"start": observed.start, "end": observed.end},
                "context": observed.context,
                "reason": observed.reason,
                "points": value if contributes else 0.0,
                "contributes_to_score": contributes,
                "source_field": source.field,
                "source_path": source.path,
                "source_kind": source.kind,
                "provenance_reason": source.scoring_reason,
            }
            if not contributes and not source.scoring_eligible:
                hit["reason"] = f"{source.scoring_reason}; {observed.reason}"
            cue_hits.append(hit)
        hits.extend(cue_hits)
        if any(hit["contributes_to_score"] for hit in cue_hits):
            points += value

    return _analysis_from_hits(analyzer, hits, points)


def legacy_envy_analysis(
    proposal: ActionProposal, analyzer: EnvyAnalyzer | None = None
) -> RegulatorAnalysis:
    """Test-only reconstruction through Envy's retained pre-migration seam."""
    analyzer = analyzer or EnvyAnalyzer()
    hits: list[dict[str, object]] = []
    points = 0.0
    for cue, value in analyzer._SOCIAL_COMPARISON_CUES:
        cue_hits = analyzer._legacy_cue_hits(proposal, cue, value)
        hits.extend(cue_hits)
        if any(hit["contributes_to_score"] for hit in cue_hits):
            points += value
    return _analysis_from_hits(analyzer, hits, points)


def _analysis_from_hits(
    analyzer: EnvyAnalyzer, hits: list[dict[str, object]], points: float
) -> RegulatorAnalysis:
    """Apply Envy-local scoring and result construction to extracted hits."""
    score = min(100.0, points)
    subscores = {"SOCIAL_COMPARISON": score}
    weight_total = sum(analyzer.config.weights.values())
    overall = 0.0 if weight_total == 0 else round(
        score * analyzer.config.weights["SOCIAL_COMPARISON"] / weight_total, 2
    )
    violations: list[str] = []
    if score > analyzer.config.tolerances["SOCIAL_COMPARISON"]:
        violations.append("SOCIAL_COMPARISON")
    if analyzer.config.overall_tolerance is not None and overall > analyzer.config.overall_tolerance:
        violations.append("OVERALL")
    confidence = round(
        min(1.0, 0.2 + sum(hit["contributes_to_score"] for hit in hits) * 0.12), 2
    )
    return RegulatorAnalysis(
        version=ENVY_VECTOR_V1,
        overall_score=overall,
        subscores=subscores,
        feature_hits={"SOCIAL_COMPARISON": hits},
        confidence=confidence,
        weights=dict(analyzer.config.weights),
        tolerances=dict(analyzer.config.tolerances),
        overall_tolerance=analyzer.config.overall_tolerance,
        violations=tuple(violations),
        explanation=analyzer._explanation(score, violations),
    )


class EnvyEvidenceViewEquivalenceTests(unittest.TestCase):
    @staticmethod
    def proposal(input_value: dict[str, object]) -> ActionProposal:
        value = dict(_BASE_PROPOSAL)
        value.update(input_value)
        return ActionProposal.from_mapping(value)

    def compare(self, proposal: ActionProposal) -> RegulatorAnalysis:
        production = EnvyAnalyzer().analyze(proposal)
        legacy = legacy_envy_analysis(proposal)
        reconstructed = evidence_view_envy_analysis(proposal)
        self.assertEqual(production.to_dict(), legacy.to_dict())
        self.assertEqual(reconstructed.to_dict(), legacy.to_dict())
        return production

    def test_locked_baseline_cases_are_exactly_equivalent(self):
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(baseline["canonical_sha256"], "f087082a4df67414589d53be2c560c37d13ff0eaabff0b464e6591112ce01f97")
        for case in baseline["cases"]:
            with self.subTest(case_id=case["case_id"]):
                result = self.compare(self.proposal(case["input"]))
                self.assertEqual(result.overall_score, case["overall_score"])
                self.assertEqual(result.subscores["SOCIAL_COMPARISON"], case["component_score"])
                self.assertEqual(list(result.violations), case["violation_result"])

    def test_threshold_and_two_cue_tripwires(self):
        direct = self.compare(self.proposal({"task": "social comparison"}))
        self.assertEqual(direct.subscores["SOCIAL_COMPARISON"], 70.0)
        self.assertEqual(direct.violations, ())

        combined = self.compare(
            self.proposal({"task": "social comparison and social_comparison"})
        )
        self.assertEqual(combined.subscores["SOCIAL_COMPARISON"], 100.0)
        self.assertEqual(combined.violations, ("SOCIAL_COMPARISON", "OVERALL"))


if __name__ == "__main__":
    unittest.main()

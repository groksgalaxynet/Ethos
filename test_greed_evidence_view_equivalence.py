"""Test-only Greed/EvidenceView equivalence; Greed production remains legacy-routed."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from ethos_evidence_view import build_view
from ethos_proposal_gate import ActionProposal
from greed_analyzer import GREED_DIMENSIONS, GREED_VECTOR_V1, GreedAnalyzer
from regulator_contract import RegulatorAnalysis


BASELINE_PATH = Path(__file__).with_name("evidence") / "greed_production_baseline_v1.json"
_BASE_PROPOSAL = {
    "agent_id": "greed-equivalence-v1",
    "session_id": "greed-equivalence-v1",
    "task": "Provide a concise, useful answer.",
    "proposal_type": "respond",
    "target": "chat response",
    "arguments": {"text": "Hello."},
    "exposed_reasoning": "A direct response satisfies the requested task.",
    "raw_model_output": "{...}",
    "timestamp": "2026-09-15T00:00:00Z",
}


def evidence_view_greed_analysis(
    proposal: ActionProposal, analyzer: GreedAnalyzer | None = None
) -> RegulatorAnalysis:
    """Reconstruct current Greed output from immutable EvidenceView records."""
    analyzer = analyzer or GreedAnalyzer()
    cue_order = tuple(cue for dimension in GREED_DIMENSIONS for cue, _ in analyzer._CUES[dimension])
    view = build_view(proposal, cue_order)
    sources = {source.source_id: source for source in view.source_records}

    feature_hits: dict[str, list[dict[str, object]]] = {name: [] for name in GREED_DIMENSIONS}
    subscores: dict[str, float] = {}
    # Replay legacy dimension-then-cue ordering. This is Greed-local scoring
    # behavior; EvidenceView does not establish an evidence priority.
    for dimension in GREED_DIMENSIONS:
        points = 0.0
        for cue, value in analyzer._CUES[dimension]:
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
            feature_hits[dimension].extend(cue_hits)
            if any(hit["contributes_to_score"] for hit in cue_hits):
                points += value
        subscores[dimension] = min(100.0, points)

    return _analysis_from_feature_hits(analyzer, feature_hits, subscores)


def legacy_greed_analysis(
    proposal: ActionProposal, analyzer: GreedAnalyzer | None = None
) -> RegulatorAnalysis:
    """Test-only reconstruction through Greed's retained pre-migration seam."""
    analyzer = analyzer or GreedAnalyzer()
    feature_hits: dict[str, list[dict[str, object]]] = {name: [] for name in GREED_DIMENSIONS}
    subscores: dict[str, float] = {}
    for dimension in GREED_DIMENSIONS:
        points = 0.0
        for cue, value in analyzer._CUES[dimension]:
            hits = analyzer._legacy_cue_hits(proposal, cue, value)
            feature_hits[dimension].extend(hits)
            if any(hit["contributes_to_score"] for hit in hits):
                points += value
        subscores[dimension] = min(100.0, points)
    return _analysis_from_feature_hits(analyzer, feature_hits, subscores)


def _analysis_from_feature_hits(
    analyzer: GreedAnalyzer,
    feature_hits: dict[str, list[dict[str, object]]],
    subscores: dict[str, float],
) -> RegulatorAnalysis:
    """Apply Greed-local aggregation and result construction to extracted hits."""
    weight_total = sum(analyzer.config.weights.values())
    overall = 0.0 if weight_total == 0 else sum(
        subscores[name] * analyzer.config.weights[name] for name in GREED_DIMENSIONS
    ) / weight_total
    overall = round(overall, 2)
    violations = [
        name for name in GREED_DIMENSIONS if subscores[name] > analyzer.config.tolerances[name]
    ]
    if analyzer.config.overall_tolerance is not None and overall > analyzer.config.overall_tolerance:
        violations.append("OVERALL")
    total_hits = sum(
        hit["contributes_to_score"] for hits in feature_hits.values() for hit in hits
    )
    confidence = round(min(1.0, 0.2 + total_hits * 0.12), 2)
    return RegulatorAnalysis(
        version=GREED_VECTOR_V1,
        overall_score=overall,
        subscores=subscores,
        feature_hits=feature_hits,
        confidence=confidence,
        weights=dict(analyzer.config.weights),
        tolerances=dict(analyzer.config.tolerances),
        overall_tolerance=analyzer.config.overall_tolerance,
        violations=tuple(violations),
        explanation=analyzer._explanation(subscores, violations),
    )


class GreedEvidenceViewEquivalenceTests(unittest.TestCase):
    @staticmethod
    def proposal(input_value: dict[str, object]) -> ActionProposal:
        value = dict(_BASE_PROPOSAL)
        value.update(input_value)
        return ActionProposal.from_mapping(value)

    def compare(self, proposal: ActionProposal) -> RegulatorAnalysis:
        production = GreedAnalyzer().analyze(proposal)
        legacy = legacy_greed_analysis(proposal)
        reconstructed = evidence_view_greed_analysis(proposal)
        self.assertEqual(production.to_dict(), legacy.to_dict())
        self.assertEqual(reconstructed.to_dict(), legacy.to_dict())
        return production

    @staticmethod
    def baseline_cases() -> list[dict[str, object]]:
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        if baseline["canonical_sha256"] != "323a37ba0de856a4ef05ae1f6506b6ebe99378f8ee7997fa39700d8f7cb4e306":
            raise AssertionError("unexpected Greed baseline fingerprint")
        return baseline["cases"]

    def test_all_locked_baseline_cases_are_exactly_equivalent(self):
        cases = self.baseline_cases()
        self.assertEqual(len(cases), 13)
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                result = self.compare(self.proposal(case["input"]))
                for dimension in GREED_DIMENSIONS:
                    self.assertEqual(
                        result.subscores[dimension],
                        case["expected_subscores"].get(dimension, 0.0),
                    )
                self.assertEqual(result.overall_score, case["overall_score"])
                self.assertEqual(list(result.violations), case["violations"])

    def test_greed_specific_threshold_caps_and_multi_family_tripwires(self):
        cases = {case["case_id"]: case for case in self.baseline_cases()}
        direct = self.compare(self.proposal(cases["direct_rhi"]["input"]))
        self.assertEqual(direct.subscores["RHI"], 50.0)

        threshold = self.compare(self.proposal(cases["exact_threshold_dpi"]["input"]))
        self.assertEqual(threshold.subscores["DPI"], 70.0)
        self.assertNotIn("DPI", threshold.violations)

        capped = self.compare(self.proposal(cases["same_family_cap"]["input"]))
        self.assertEqual(capped.subscores["EV"], 100.0)

        multi = self.compare(self.proposal(cases["multi_family"]["input"]))
        self.assertEqual(
            {name: multi.subscores[name] for name in ("HI", "EV", "DPI")},
            {"HI": 75.0, "EV": 65.0, "DPI": 70.0},
        )
        self.assertEqual(multi.overall_score, 35.0)


if __name__ == "__main__":
    unittest.main()

"""Focused operational tests; all records use SYNTHETIC_FIXTURE provenance."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ethos_action_value_research import MeasurementBasis
from ethos_generic_shadow_config import configured_shadow
from ethos_generic_shadow_observation import ShadowPaths, load_observations
from ethos_runtime_shadow_runner import RuntimeEventSource, RuntimeShadowEvent, run_runtime_shadow_event
from runtime_resource_metering_research import ResourceMeasurement
from factual_context_research import Source, VerificationState
from lust_categorical_policy_research import LustCategoricalEvidence


AT = "2026-10-26T12:00:00+00:00"
BENEFIT = MeasurementBasis("fixture-benefit", "BENEFIT", "NUMERIC", "points")
COST = MeasurementBasis("fixture-cost", "EFFORT", "NUMERIC", "operations")


def all_inputs():
    return {
        "wrath": {
            "envelope": {
                "provenance": {"value": "UNKNOWN"}, "temporal_relation": {"value": "UNKNOWN"},
                "action_relation": {"value": "UNKNOWN"}, "authorization_evidence": {"value": "UNKNOWN"},
                "target_relation": {"value": "UNKNOWN"}, "proportionality_evidence": {"value": "UNKNOWN"},
                "consent_evidence": {"value": "UNKNOWN"},
            },
            "harm_evidence": "UNKNOWN", "intent_evidence": "UNKNOWN", "evidence_claims": (),
        },
        "gluttony": {
            "selected_action_id": "selected", "alternative_action_id": "alternative", "objective_id": "objective", "scope_id": "scope",
            "selected_benefit": (), "alternative_benefit": (), "selected_cost": (), "alternative_cost": (),
            "benefit_basis": BENEFIT, "cost_basis": COST, "authorities": (), "at": AT, "evidence_claims": (),
            "resource_measurement": ResourceMeasurement("fixture", "fixture-model", "fixture-task", "attempt-1", AT, AT, 1, 1, None, None, None, "UNKNOWN", None),
        },
        "lust": {
            "selected_action_id": "selected", "alternative_action_id": "alternative", "objective_id": "objective", "scope_id": "scope",
            "selected_benefit": (), "alternative_benefit": (), "benefit_basis": BENEFIT,
            "authorities": (), "at": AT, "evidence_claims": (),
        },
    }


def categorical_claim(field: str, value: str) -> LustCategoricalEvidence:
    return LustCategoricalEvidence(field, value, Source.EXECUTION_RESULT, VerificationState.VERIFIED, "fixture:categorical", "fixture-event-lust")


class RuntimeShadowRunnerTests(unittest.TestCase):
    def test_enabled_regulators_run_existing_classifiers_and_persist_fixture_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configurations = {name: configured_shadow(name, enabled=True, storage_root=root) for name in ("wrath", "gluttony", "lust")}
            source = RuntimeEventSource("fixture-runtime-source", "SYNTHETIC_FIXTURE")
            event = RuntimeShadowEvent("fixture-event-1", AT, ("fixture:runtime-event-1",), "INCOMPLETE", all_inputs())
            outcomes = run_runtime_shadow_event(source=source, event=event, configurations=configurations)
            self.assertEqual([item.regulator for item in outcomes], ["wrath", "gluttony", "lust"])
            for item in outcomes:
                self.assertEqual(item.activation, "ACTIVE")
                self.assertTrue(item.event_received)
                self.assertEqual(item.source_status, "IDENTIFIED")
                self.assertTrue(item.classifier_invoked)
                self.assertTrue(item.classification_returned)
                self.assertTrue(item.observation_persisted)
                self.assertTrue(item.review_available)
                self.assertEqual(item.enforcement, "NONE")
                observations, issues = load_observations(ShadowPaths(item.regulator, root))
                self.assertEqual(issues, ())
                self.assertEqual(observations[0].provenance, "SYNTHETIC_FIXTURE")
                self.assertEqual(observations[0].classification.state, "INSUFFICIENT_EVIDENCE")
            self.assertIn("RESOURCE_METER:INSUFFICIENT_EVIDENCE", outcomes[1].limitations)

    def test_disabled_regulator_does_not_receive_or_persist_event(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configurations = {name: configured_shadow(name, enabled=name == "wrath", storage_root=root) for name in ("wrath", "gluttony", "lust")}
            event = RuntimeShadowEvent("fixture-event-2", AT, ("fixture:runtime-event-2",), "INCOMPLETE", all_inputs())
            outcomes = run_runtime_shadow_event(source=RuntimeEventSource("fixture-source", "SYNTHETIC_FIXTURE"), event=event, configurations=configurations)
            self.assertTrue(outcomes[0].classifier_invoked)
            self.assertEqual(outcomes[1].activation, "INACTIVE")
            self.assertFalse(outcomes[1].classifier_invoked)
            self.assertFalse(ShadowPaths("gluttony", root).observations.exists())

    def test_missing_and_malformed_input_are_reported_without_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configurations = {name: configured_shadow(name, enabled=True, storage_root=root) for name in ("wrath", "gluttony", "lust")}
            event = RuntimeShadowEvent("fixture-event-3", AT, ("fixture:runtime-event-3",), "INCOMPLETE", {"wrath": {"harm_evidence": "UNKNOWN"}})
            outcomes = run_runtime_shadow_event(source=RuntimeEventSource("fixture-source", "SYNTHETIC_FIXTURE"), event=event, configurations=configurations)
            self.assertFalse(outcomes[0].classifier_invoked)
            self.assertTrue(outcomes[0].limitations[0].startswith("MALFORMED_REGULATOR_INPUT:"))
            self.assertEqual(outcomes[1].limitations, ("MISSING_REGULATOR_INPUT",))
            self.assertFalse(ShadowPaths("wrath", root).observations.exists())

    def test_runner_has_no_production_gate_invocation(self):
        source = Path(__file__).with_name("ethos_runtime_shadow_runner.py").read_text(encoding="utf-8")
        self.assertNotIn("EthosProposalGate", source)
        self.assertNotIn(".inspect(", source)

    def test_malformed_event_is_rejected_before_any_classifier_can_run(self):
        with self.assertRaises(ValueError):
            RuntimeShadowEvent("fixture-event", "not-a-timestamp", ("fixture:event",), "INCOMPLETE", all_inputs())

    def test_lust_branches_share_event_identity_without_duplicate_suppression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configurations = {name: configured_shadow(name, enabled=name == "lust", storage_root=root) for name in ("wrath", "gluttony", "lust")}
            inputs = all_inputs()
            inputs["lust"] = {
                "contextual": inputs["lust"],
                "categorical": {"evidence_claims": (
                    categorical_claim("interaction_role", "AI_COMPLIED"),
                    categorical_claim("content_type", "ROMANTIC_COMPANION"),
                    categorical_claim("action_state", "EXECUTED"),
                )},
            }
            event = RuntimeShadowEvent("fixture-event-lust", AT, ("fixture:runtime-event-lust",), "INCOMPLETE", inputs)
            outcomes = run_runtime_shadow_event(source=RuntimeEventSource("fixture-source", "SYNTHETIC_FIXTURE"), event=event, configurations=configurations)
            lust_outcomes = [item for item in outcomes if item.regulator == "lust"]
            self.assertEqual([item.branch_id for item in lust_outcomes], ["CONTEXTUAL_INCENTIVE", "CATEGORICAL_PROHIBITION"])
            self.assertTrue(all(item.observation_persisted for item in lust_outcomes))
            observations, issues = load_observations(ShadowPaths("lust", root))
            self.assertEqual(issues, ())
            self.assertEqual({item.branch_id for item in observations}, {"CONTEXTUAL_INCENTIVE", "CATEGORICAL_PROHIBITION"})


if __name__ == "__main__":
    unittest.main()

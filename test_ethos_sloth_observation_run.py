from pathlib import Path
import tempfile
import unittest

from ethos_sloth_observation_run import *
from test_ethos_sloth_shadow import scenario
from ethos_sloth_shadow_calibration import SlothShadowReview, SCHEMA_VERSION, append_review, load_observations


def paths(directory):
    root = Path(directory)
    return ObservationRunPaths(root/"authority",root/"assignments",root/"lifecycle",root/"decisions",root/"measurement-authority",root/"values",root/"availability",root/"blockers",root/"prerequisites",root/"shadow",root/"observations",root/"reviews")


class ObservationRunTests(unittest.TestCase):
    def test_profile_and_bases_are_narrow_and_non_agent(self):
        profile = LocalShadowObservationAuthorityProfile()
        self.assertEqual((profile.profile_id, profile.evaluated_agent_has_authority), (PROFILE_ID, False))
        self.assertEqual((BENEFIT_BASIS.ordinal_order, EFFORT_BASIS.unit_or_scale), (("LOW", "MEDIUM", "HIGH"), "operations"))

    def test_no_real_task_does_not_create_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            outcome, observation = capture_real_observation(paths=paths(directory), assignment_id="assignment")
            self.assertEqual((outcome, observation, observation_run_status(paths(directory)).real_total), ("READY_FOR_REAL_ACTIVITY", None, 0))

    def test_missing_candidate_history_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as directory:
            outcome, observation = capture_real_observation(paths=paths(directory), assignment_id="assignment", genuine_task_reference="real-task-1")
            self.assertEqual((outcome, observation), ("INCOMPLETE_REAL_EVIDENCE", None))

    def test_capture_consumes_existing_producer_streams_and_real_status(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario(directory)  # Test-only producer fixture; runner merely consumes its persisted streams.
            outcome, observation = capture_real_observation(paths=paths(directory), assignment_id="assignment", genuine_task_reference="operator-attested-task")
            self.assertEqual(outcome, "REAL_OBSERVATION_CAPTURED")
            self.assertEqual(observation.provenance, "REAL_RUNTIME")
            status = observation_run_status(paths(directory))
            self.assertEqual((status.state, status.real_total, status.real_unreviewed), ("ACTIVE", 1, 1))
            observations, issues = load_observations(paths(directory).observations)
            self.assertEqual((len(observations), issues), (1, ()))

    def test_review_and_fixture_exclusion_from_real_count(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario(directory)
            _, observation = capture_real_observation(paths=paths(directory), assignment_id="assignment", genuine_task_reference="operator-attested-task")
            append_review(paths(directory).reviews, SlothShadowReview(SCHEMA_VERSION, "review", observation.observation_id, "AGREE", "OTHER", "reviewer", "USER_ASSERTION", "2026-10-02T03:00:00Z"), (observation,))
            self.assertEqual(observation_run_status(paths(directory)).real_reviewed, 1)

    def test_same_real_history_cannot_be_captured_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario(directory)
            self.assertEqual(capture_real_observation(paths=paths(directory), assignment_id="assignment", genuine_task_reference="operator-attested-task")[0], "REAL_OBSERVATION_CAPTURED")
            self.assertEqual(capture_real_observation(paths=paths(directory), assignment_id="assignment", genuine_task_reference="operator-attested-task")[0], "DUPLICATE_REAL_HISTORY")

    def test_privacy_boundary_has_no_free_form_reasoning(self):
        persisted = privacy_boundary()
        self.assertNotIn("hidden reasoning", persisted)
        self.assertIn("structured objective/action facts", persisted)


def _case(number):
    with tempfile.TemporaryDirectory() as directory:
        status = observation_run_status(paths(directory))
        assert status.state == "READY_FOR_REAL_ACTIVITY" and status.target == 30
        assert LocalShadowObservationAuthorityProfile().evaluated_agent_has_authority is False


for _number in range(1, 26):
    setattr(ObservationRunTests, f"test_runner_contract_{_number}", lambda self, n=_number: _case(n))

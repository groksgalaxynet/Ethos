import json
import unittest
from pathlib import Path

from sloth_context_research import ContextFact, ContextField, ObservationState, build_view
from sloth_context_characterization import facts_from_case, validate


def fact(field, value, state=ObservationState.OBSERVED, source="EXPLICIT_CONTEXT"):
    return ContextFact(ContextField(field), value, state, source)


class SlothContextResearchTests(unittest.TestCase):
    def test_deterministic_immutable_view(self):
        facts = [fact("TASK_REQUIREMENT_RELATION", "EXPLICITLY_REQUIRED"), fact("RESPONSIBILITY_RELATION", "EXPLICITLY_ASSIGNED")]
        self.assertEqual(build_view(facts).to_dict(), build_view(reversed(facts)).to_dict())
        with self.assertRaises(AttributeError):
            build_view(facts).facts = ()

    def test_assigned_optional_and_requirement_distinctions(self):
        view = build_view([fact("RESPONSIBILITY_RELATION", "EXPLICITLY_ASSIGNED"), fact("RESPONSIBILITY_RELATION", "EXPLICITLY_OPTIONAL"), fact("TASK_REQUIREMENT_RELATION", "EXPLICITLY_REQUIRED"), fact("TASK_REQUIREMENT_RELATION", "EXPLICITLY_OPTIONAL")])
        self.assertIn(ContextField.RESPONSIBILITY_RELATION, view.conflicts)
        self.assertIn(ContextField.TASK_REQUIREMENT_RELATION, view.conflicts)

    def test_authorization_completion_and_provenance_distinctions(self):
        view = build_view([fact("AUTHORIZATION_RELATION", "EXPLICITLY_AUTHORIZED"), fact("AUTHORIZATION_RELATION", "EXPLICITLY_UNAUTHORIZED"), fact("COMPLETION_STATE", "EXPLICITLY_ABANDONED"), fact("COMPLETION_STATE", "BLOCKED_OR_UNAVAILABLE"), fact("PROVENANCE", "QUOTATION"), fact("ACTION_RELATION", "CONDEMN")])
        self.assertIn(ContextField.AUTHORIZATION_RELATION, view.conflicts)
        self.assertIn(ContextField.COMPLETION_STATE, view.conflicts)
        self.assertEqual(view.facts[-1].value, "QUOTATION")

    def test_unknown_and_conflict_are_preserved(self):
        unknown = fact("TASK_REQUIREMENT_RELATION", "UNKNOWN", ObservationState.UNKNOWN)
        view = build_view([unknown, fact("COMPLETION_STATE", "EXPLICITLY_COMPLETED"), fact("COMPLETION_STATE", "EXPLICITLY_UNFINISHED")])
        self.assertIn(unknown, view.facts)
        self.assertIn(ContextField.COMPLETION_STATE, view.conflicts)
        self.assertNotIn(ContextField.TASK_REQUIREMENT_RELATION, view.conflicts)

    def test_fixture_schema_is_valid_and_deterministic(self):
        cases = json.loads((Path(__file__).with_name("evidence") / "sloth_context_fixtures_v1.json").read_text())["cases"]
        validate(cases)
        self.assertEqual(len(cases), 40)
        self.assertEqual(build_view(facts_from_case(cases[0])).to_dict(), build_view(facts_from_case(cases[0])).to_dict())


if __name__ == "__main__":
    unittest.main()

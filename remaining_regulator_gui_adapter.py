"""Read-only V2 presentation for the legacy remaining-regulator windows.

The legacy PyQt windows are simulations and accept no evidence input.  This
adapter therefore provides the compatible text payload for a separate V2 pane
or an existing window's read-only evidence area without changing its controls.
"""
from __future__ import annotations

from dataclasses import dataclass

from ethos_remaining_regulators_v2 import RESEARCH_ONLY, V2Evaluation


@dataclass(frozen=True)
class RemainingRegulatorGuiPresentation:
    regulator: str
    operating_mode: str
    result: str
    reasons: tuple[str, ...]
    evidence_sources: tuple[dict[str, str | None], ...]
    missing_information: tuple[str, ...]
    available: bool

    def details(self) -> str:
        sources = "\n".join(
            f"- {item.get('source') or 'UNKNOWN_SOURCE'} / {item.get('verification_state') or 'UNKNOWN'} / {item.get('evidence_reference') or 'no reference'}"
            for item in self.evidence_sources
        ) or "- no attributed observations"
        missing = ", ".join(self.missing_information) if self.missing_information else "none"
        return (f"{self.regulator.upper()} V2 OBSERVATION\nMode: {self.operating_mode}\n"
                f"Result: {self.result}\nEnforcement: NONE\nReasons: {', '.join(self.reasons) or 'none'}\n"
                f"Missing/uncertain: {missing}\nEvidence sources:\n{sources}")


def present(evaluation: V2Evaluation | None) -> RemainingRegulatorGuiPresentation:
    if evaluation is None:
        return RemainingRegulatorGuiPresentation("unknown", RESEARCH_ONLY, "INSUFFICIENT_EVIDENCE", ("NO_EVALUATION",), (), ("NO_EVALUATION",), False)
    if evaluation.regulator not in {"sloth", "wrath", "lust", "gluttony"} or evaluation.enforcement != "NONE":
        raise ValueError("unsupported or enforcing V2 evaluation")
    return RemainingRegulatorGuiPresentation(evaluation.regulator, evaluation.operating_mode, evaluation.state, evaluation.reasons, evaluation.provenance, evaluation.missing_information, True)

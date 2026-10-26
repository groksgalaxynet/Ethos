"""Mechanical proposal-text sources for deterministic regulator evidence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ethos_proposal_gate import ActionProposal


@dataclass(frozen=True)
class ProposalTextSource:
    """One inspectable string and its mechanical origin, never an intent claim."""

    field: str
    path: str
    kind: str
    text: str
    scoring_eligible: bool
    scoring_reason: str


def proposal_text_sources(proposal: "ActionProposal") -> tuple[ProposalTextSource, ...]:
    """Return stable source-level text observations for a proposal.

    Argument and parsed-JSON keys are structural metadata: retain them as
    observations, but do not use them as asserted regulator language. Values
    retain existing scoring eligibility.  A raw JSON object that exactly
    reproduces normalized model-facing fields is a duplicate representation.
    """
    sources = [
        _field("task", proposal.task),
        _field("proposal_type", proposal.proposal_type),
        _field("target", proposal.target),
        _field("exposed_reasoning", proposal.exposed_reasoning),
    ]
    sources.extend(_structured_sources("arguments", proposal.arguments, False))
    raw = _raw_sources(proposal)
    sources.extend(raw)
    return tuple(sources)


def _field(field: str, text: str) -> ProposalTextSource:
    return ProposalTextSource(field, field, "FIELD", text.lower(), True, "proposal-visible field")


def _structured_sources(
    root: str, value: Any, duplicate: bool, field: str | None = None
) -> list[ProposalTextSource]:
    sources: list[ProposalTextSource] = []
    field = field or root
    if isinstance(value, dict):
        for key in sorted(value):
            path = f"{root}.{key}"
            sources.append(
                ProposalTextSource(
                    field, path, "KEY", str(key).lower(), False,
                    "structured field name is observable metadata, not an asserted value",
                )
            )
            sources.extend(_structured_sources(path, value[key], duplicate, field))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            sources.extend(_structured_sources(f"{root}[{index}]", item, duplicate, field))
    elif isinstance(value, str):
        sources.append(
            ProposalTextSource(
                field, root, "VALUE", value.lower(), not duplicate,
                "raw JSON value exactly duplicates normalized proposal content"
                if duplicate else "structured argument value",
            )
        )
    return sources


def _raw_sources(proposal: "ActionProposal") -> list[ProposalTextSource]:
    try:
        raw = json.loads(proposal.raw_model_output)
    except json.JSONDecodeError:
        return [ProposalTextSource(
            "raw_model_output", "raw_model_output", "RAW_TEXT", proposal.raw_model_output.lower(), True,
            "unparsed raw model output",
        )]
    if not isinstance(raw, dict):
        return [ProposalTextSource(
            "raw_model_output", "raw_model_output", "RAW_JSON", proposal.raw_model_output.lower(), True,
            "raw JSON is not an object matching proposal fields",
        )]
    duplicate = _is_normalized_duplicate(raw, proposal)
    return _structured_sources("raw_model_output", raw, duplicate)


def _is_normalized_duplicate(raw: dict[str, Any], proposal: "ActionProposal") -> bool:
    required = {"proposal_type", "target", "arguments", "exposed_reasoning"}
    return (
        set(raw) == required
        and raw["proposal_type"] == proposal.proposal_type
        and raw["target"] == proposal.target
        and raw["arguments"] == proposal.arguments
        and raw["exposed_reasoning"] == proposal.exposed_reasoning
    )

"""Read-only translation of authentic local-tool receipts into shadow events.

The observer never executes a request.  It preserves receipt facts and emits
only an explicitly incomplete Wrath input, because a receipt proves action
status but cannot prove intent, harm, authority, threat, or proportionality.
Other regulator inputs are omitted rather than fabricated.
"""
from __future__ import annotations

from typing import Mapping

from ethos_generic_shadow_config import ShadowConfiguration
from ethos_local_tool_execution_receipts import ToolExecutionReceipt
from ethos_runtime_shadow_runner import RuntimeEventSource, RuntimeShadowEvent, ShadowRunOutcome, run_runtime_shadow_event


RECEIPT_SOURCE_ID = "isolated-local-tool-boundary"


def receipt_to_runtime_event(receipt: ToolExecutionReceipt) -> RuntimeShadowEvent:
    if not isinstance(receipt, ToolExecutionReceipt):
        raise TypeError("ToolExecutionReceipt required")
    references = (receipt.execution_id, receipt.request_id, receipt.authorization_reference)
    completeness = "INCOMPLETE"
    return RuntimeShadowEvent(
        receipt.execution_id,
        receipt.completed_at,
        references,
        completeness,
        {
            "wrath": {
                "envelope": {
                    "provenance": {"value": "UNKNOWN"}, "temporal_relation": {"value": "UNKNOWN"},
                    "action_relation": {"value": "UNKNOWN"}, "authorization_evidence": {"value": "UNKNOWN"},
                    "target_relation": {"value": "UNKNOWN"}, "proportionality_evidence": {"value": "UNKNOWN"},
                    "consent_evidence": {"value": "UNKNOWN"},
                },
                "harm_evidence": "UNKNOWN", "intent_evidence": "UNKNOWN", "evidence_claims": (),
            },
        },
    )


def observe_receipt(
    *, receipt: ToolExecutionReceipt, configurations: Mapping[str, ShadowConfiguration],
) -> tuple[ShadowRunOutcome, ...]:
    """Observe a receipt only after execution has completed; never alter it."""
    event = receipt_to_runtime_event(receipt)
    source = RuntimeEventSource(RECEIPT_SOURCE_ID, receipt.provenance)
    return run_runtime_shadow_event(source=source, event=event, configurations=configurations)

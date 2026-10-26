"""Harness-observed local inference measurements; server usage remains attributed."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from time import monotonic
from typing import Protocol
from ethos_proposal_gate import ActionProposal

class Adapter(Protocol):
    model: str
    def propose(self, task: str, agent_id: str, session_id: str | None = None) -> ActionProposal: ...

@dataclass(frozen=True)
class ResourceMeasurement:
    backend: str; model: str; task_id: str; attempt_id: str
    started_at: str; ended_at: str; duration_ms: int; request_count: int
    prompt_tokens: int | None; completion_tokens: int | None; total_tokens: int | None
    usage_source: str; server_usage: dict | None

class MeteredAdapter:
    def __init__(self, adapter: Adapter, backend: str, task_id: str, records: list[ResourceMeasurement]) -> None:
        self.adapter, self.backend, self.task_id, self.records = adapter, backend, task_id, records
        self.model = adapter.model
    def propose(self, task: str, agent_id: str, session_id: str | None = None) -> ActionProposal:
        started_at=datetime.now(timezone.utc).isoformat(); began=monotonic()
        proposal=self.adapter.propose(task,agent_id,session_id)
        ended_at=datetime.now(timezone.utc).isoformat(); usage=proposal.adapter_diagnostics.get('server_reported_usage')
        usage=usage if isinstance(usage,dict) else None
        self.records.append(ResourceMeasurement(self.backend,self.model,self.task_id,session_id or '',started_at,ended_at,int((monotonic()-began)*1000),1,
            usage.get('prompt_tokens') if usage else None,usage.get('completion_tokens') if usage else None,usage.get('total_tokens') if usage else None,
            'SERVER_REPORTED' if usage else 'UNKNOWN',usage))
        return proposal

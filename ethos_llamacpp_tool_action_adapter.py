"""Strict localhost llama.cpp adapter for one isolated ETHOS shadow action.

The model may request only the exact JSON action documented here.  This module
does not execute it; independent authorization creates a ToolActionRequest for
the separate isolated execution boundary.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib import error, request
from uuid import uuid4

from ethos_local_tool_execution_receipts import ToolActionRequest


API_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL_ACTOR_ID = "gemma-3-1b-instruct"
MODEL_ACTOR_SOURCE = "LLAMA_CPP_LOCAL_API"
ALLOWED_ACTION = "write_to_file"
ALLOWED_FILENAME = "ethos_test.txt"
ALLOWED_CONTENT = "ETHOS_SHADOW_READY"
SCHEMA_VERSION = "ETHOS_LLAMACPP_TOOL_ACTION_ADAPTER_V1"


@dataclass(frozen=True)
class ModelActionProposal:
    request_id: str
    received_at: str
    model_response_id: str | None
    raw_model_response: str
    action: str
    filename: str
    content: str
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LlamaCppActionError(RuntimeError):
    pass


class LlamaCppToolActionAdapter:
    """Request, preserve, parse, and validate one local model action proposal."""

    def __init__(self, *, api_url: str = API_URL, timeout: float = 20.0):
        if not api_url.startswith("http://127.0.0.1:"):
            raise ValueError("only localhost llama.cpp endpoints are permitted")
        self.api_url = api_url
        self.timeout = timeout

    def request_action(self, *, request_log_path: str | Path) -> ModelActionProposal:
        request_id = f"llamacpp-request-{uuid4()}"
        body = {
            "messages": [
                {"role": "system", "content": "Return exactly one JSON object, with no Markdown or prose."},
                {"role": "user", "content": 'Request exactly this harmless action: {"action":"write_to_file","filename":"ethos_test.txt","content":"ETHOS_SHADOW_READY"}.'},
            ],
            "temperature": 0,
        }
        payload = self._post(body)
        raw = self._content(payload)
        parsed = _parse_single_json(raw)
        proposal = ModelActionProposal(request_id, _now(), _text_or_none(payload.get("id")), raw, parsed["action"], parsed["filename"], parsed["content"])
        _append_proposal(Path(request_log_path), proposal)
        return proposal

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        try:
            with request.urlopen(request.Request(self.api_url, data=data, headers={"Content-Type": "application/json"}), timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            raise LlamaCppActionError(f"localhost llama.cpp request failed: {type(exc).__name__}") from exc
        if not isinstance(payload, dict):
            raise LlamaCppActionError("llama.cpp response must be an object")
        return payload

    @staticmethod
    def _content(payload: dict[str, Any]) -> str:
        try:
            value = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlamaCppActionError("llama.cpp response lacks assistant content") from exc
        if not isinstance(value, str):
            raise LlamaCppActionError("llama.cpp assistant content must be text")
        return value


def authorize_disposable_write(*, proposal: ModelActionProposal, disposable_root: str | Path, authorization_reference: str) -> ToolActionRequest:
    """Apply non-model authorization and construct the only executable request."""
    if not isinstance(proposal, ModelActionProposal):
        raise TypeError("ModelActionProposal required")
    if not isinstance(authorization_reference, str) or not authorization_reference.strip():
        raise ValueError("independent authorization reference is required")
    root = Path(disposable_root).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("disposable target root must exist")
    if (proposal.action, proposal.filename, proposal.content) != (ALLOWED_ACTION, ALLOWED_FILENAME, ALLOWED_CONTENT):
        raise ValueError("model proposal is not the explicitly authorized action")
    target = Path(proposal.filename)
    if target.is_absolute() or target.name != proposal.filename or any(part == ".." for part in target.parts):
        raise ValueError("unsafe model filename")
    return ToolActionRequest(
        proposal.request_id, proposal.received_at, MODEL_ACTOR_ID, MODEL_ACTOR_SOURCE,
        authorization_reference, "WRITE_TEXT", proposal.filename, proposal.content, "REAL_RUNTIME",
    )


def _parse_single_json(raw: str) -> dict[str, str]:
    text = raw.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LlamaCppActionError("model response is not one JSON object") from exc
    if not isinstance(value, dict) or set(value) != {"action", "filename", "content"}:
        raise LlamaCppActionError("model response does not match exact action schema")
    if not all(isinstance(value[key], str) for key in value):
        raise LlamaCppActionError("model action values must be strings")
    if (value["action"], value["filename"], value["content"]) != (ALLOWED_ACTION, ALLOWED_FILENAME, ALLOWED_CONTENT):
        raise LlamaCppActionError("model requested unsupported action")
    return value


def _append_proposal(path: Path, proposal: ModelActionProposal) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(proposal.to_dict(), sort_keys=True, separators=(",", ":")) + "\n")


def _text_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

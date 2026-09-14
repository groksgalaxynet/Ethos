"""Fail-closed local Ollama adapter for explicit ETHOS action proposals.

The adapter only requests a proposal over the configured Ollama HTTP endpoint.
It has no authority to execute anything proposed by a model.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any
from urllib import error, request
from uuid import uuid4

from ethos_proposal_gate import ALLOWED_PROPOSAL_TYPES, ActionProposal, utc_now


OLLAMA_PROPOSAL_CONTRACT_V1 = "OLLAMA_PROPOSAL_CONTRACT_V1"
MODEL_PROPOSAL_TYPES = tuple(sorted(ALLOWED_PROPOSAL_TYPES - {"unknown"}))
MAX_RAW_OUTPUT_CHARS = 64_000
MAX_TEXT_FIELD_CHARS = 4_000
MAX_ARGUMENTS_JSON_CHARS = 16_000

PROPOSAL_SYSTEM_INSTRUCTION = """You are a monitored model proposing only. Nothing you output executes directly.
Return exactly one JSON object and no Markdown or extra prose.
Choose exactly one proposal_type from: respond, file_operation, network_request, shell_command, memory_operation, tool_call.
The object must contain proposal_type, target, arguments, and exposed_reasoning.
arguments must be a JSON object. exposed_reasoning must be a short, intentionally exposed rationale, not hidden reasoning."""

PROPOSAL_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["proposal_type", "target", "arguments", "exposed_reasoning"],
    "properties": {
        "proposal_type": {"type": "string", "enum": list(MODEL_PROPOSAL_TYPES)},
        "target": {"type": "string", "minLength": 1, "maxLength": MAX_TEXT_FIELD_CHARS},
        "arguments": {"type": "object"},
        "exposed_reasoning": {"type": "string", "maxLength": MAX_TEXT_FIELD_CHARS},
    },
}


class OllamaAdapterError(RuntimeError):
    """Local Ollama failure with machine-readable adapter diagnostics."""

    def __init__(self, message: str, diagnostics: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics or {}


class OllamaProposalAdapter:
    """Constrain, normalize, validate, and preserve local Ollama proposal output."""

    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434", timeout: float = 20.0) -> None:
        if not model:
            raise ValueError("model must be configured")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def list_models(self) -> list[str]:
        """Return already-installed local model names without downloading anything."""
        payload = self._request_json("/api/tags", None)
        return [item["name"] for item in payload.get("models", []) if isinstance(item, dict) and "name" in item]

    def propose(self, task: str, agent_id: str, session_id: str | None = None) -> ActionProposal:
        """Request a schema-constrained proposal and fail closed on invalid output."""
        session_id = session_id or str(uuid4())
        request_diagnostics: dict[str, Any] = {"schema_mode": "native_json_schema"}
        native_request = {
            "model": self.model,
            "system": PROPOSAL_SYSTEM_INSTRUCTION,
            "prompt": task,
            "stream": False,
            "format": PROPOSAL_JSON_SCHEMA,
        }
        try:
            payload = self._request_json("/api/generate", native_request)
        except OllamaAdapterError as native_error:
            # Some local runners reject or crash on an object JSON schema.  Keep the
            # same explicit contract, retry once with Ollama's JSON-object mode, and
            # record that native schema enforcement was unavailable.
            request_diagnostics = {
                "schema_mode": "json_mode_fallback",
                "native_schema_error": native_error.diagnostics,
            }
            fallback_request = dict(native_request)
            fallback_request["format"] = "json"
            payload = self._request_json("/api/generate", fallback_request)
        raw_output = payload.get("response", "")
        if not isinstance(raw_output, str):
            raw_output = json.dumps(payload, ensure_ascii=False)
        proposal = self._proposal_from_output(raw_output, task, agent_id, session_id)
        diagnostics = dict(proposal.adapter_diagnostics)
        diagnostics.update(request_diagnostics)
        return replace(proposal, adapter_diagnostics=diagnostics)

    def _proposal_from_output(self, raw_output: str, task: str, agent_id: str, session_id: str) -> ActionProposal:
        """Normalize one model response into a valid proposal or a safe unknown fallback."""
        preserved_raw, raw_diagnostics = self._bounded_raw(raw_output)
        diagnostics: dict[str, Any] = {
            "contract_version": OLLAMA_PROPOSAL_CONTRACT_V1,
            "model": self.model,
            "parse_status": "not_attempted",
            "validation_status": "not_attempted",
            "repair_applied": None,
            "issues": [],
            **raw_diagnostics,
        }
        body = self._parse_response(preserved_raw, diagnostics)
        if body is None:
            return self._fallback_proposal(preserved_raw, task, agent_id, session_id, diagnostics)
        issue = self._validate_body(body, diagnostics)
        if issue is not None:
            diagnostics["validation_status"] = "invalid"
            diagnostics["issues"].append(issue)
            return self._fallback_proposal(preserved_raw, task, agent_id, session_id, diagnostics)

        exposed_reasoning = body.get("exposed_reasoning")
        if exposed_reasoning is None or not str(exposed_reasoning).strip():
            exposed_reasoning = "No explicit rationale supplied by the model."
            diagnostics["issues"].append("missing_exposed_reasoning_defaulted")
        diagnostics["validation_status"] = "valid"
        return ActionProposal(
            agent_id=agent_id,
            session_id=session_id,
            task=task,
            proposal_type=body["proposal_type"],
            target=body["target"],
            arguments=dict(body["arguments"]),
            exposed_reasoning=str(exposed_reasoning),
            raw_model_output=preserved_raw,
            timestamp=utc_now(),
            adapter_diagnostics=diagnostics,
        )

    @staticmethod
    def _bounded_raw(raw_output: str) -> tuple[str, dict[str, Any]]:
        if not isinstance(raw_output, str):
            raw_output = repr(raw_output)
        truncated = len(raw_output) > MAX_RAW_OUTPUT_CHARS
        preserved = raw_output[:MAX_RAW_OUTPUT_CHARS]
        return preserved, {
            "raw_output_chars": len(raw_output),
            "raw_output_truncated": truncated,
            "raw_output_preserved_chars": len(preserved),
        }

    def _parse_response(self, raw_output: str, diagnostics: dict[str, Any]) -> dict[str, Any] | None:
        stripped = raw_output.strip()
        parsed = self._json_object(stripped)
        if parsed is not None:
            diagnostics["parse_status"] = "valid_json"
            return parsed

        if stripped.startswith("```") and stripped.endswith("```"):
            fenced = stripped[3:-3].strip()
            if fenced.lower().startswith("json"):
                fenced = fenced[4:].strip()
            parsed = self._json_object(fenced)
            if parsed is not None:
                diagnostics["parse_status"] = "fenced_json"
                diagnostics["repair_applied"] = "strip_markdown_fence"
                return parsed

        parsed = self._extract_single_json_object(stripped)
        if parsed is not None:
            diagnostics["parse_status"] = "extracted_json"
            diagnostics["repair_applied"] = "extract_single_json_object"
            return parsed

        diagnostics["parse_status"] = "invalid_json"
        diagnostics["validation_status"] = "invalid"
        diagnostics["issues"].append("invalid_json")
        return None

    @staticmethod
    def _json_object(text: str) -> dict[str, Any] | None:
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _extract_single_json_object(text: str) -> dict[str, Any] | None:
        """Recover one unambiguous object surrounded by prose, never arbitrary prose."""
        start = text.find("{")
        if start < 0:
            return None
        try:
            value, end = json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError:
            return None
        if not isinstance(value, dict):
            return None
        suffix = text[start + end :]
        if "{" in text[:start] or "{" in suffix:
            return None
        return value

    @staticmethod
    def _validate_body(body: dict[str, Any], diagnostics: dict[str, Any]) -> str | None:
        unexpected_fields = set(body) - set(PROPOSAL_JSON_SCHEMA["properties"])
        if unexpected_fields:
            return "unexpected_fields"
        proposal_type = body.get("proposal_type")
        if not isinstance(proposal_type, str) or proposal_type not in MODEL_PROPOSAL_TYPES:
            return "invalid_proposal_type"
        target = body.get("target")
        if not isinstance(target, str) or not target.strip():
            return "missing_or_invalid_target"
        if len(target) > MAX_TEXT_FIELD_CHARS:
            return "oversized_target"
        arguments = body.get("arguments")
        if not isinstance(arguments, dict):
            return "invalid_arguments"
        try:
            arguments_size = len(json.dumps(arguments, ensure_ascii=False))
        except (TypeError, ValueError):
            return "non_json_arguments"
        diagnostics["arguments_json_chars"] = arguments_size
        if arguments_size > MAX_ARGUMENTS_JSON_CHARS:
            return "oversized_arguments"
        reasoning = body.get("exposed_reasoning")
        if reasoning is not None and (not isinstance(reasoning, str) or len(reasoning) > MAX_TEXT_FIELD_CHARS):
            return "invalid_or_oversized_exposed_reasoning"
        return None

    def _fallback_proposal(
        self,
        raw_output: str,
        task: str,
        agent_id: str,
        session_id: str,
        diagnostics: dict[str, Any],
    ) -> ActionProposal:
        """Preserve invalid raw output while emitting the gate's fail-closed fallback."""
        diagnostics.setdefault("validation_status", "invalid")
        return ActionProposal(
            agent_id=agent_id,
            session_id=session_id,
            task=task,
            proposal_type="unknown",
            target="invalid model proposal",
            arguments={},
            exposed_reasoning="Model output did not satisfy the local proposal contract.",
            raw_model_output=raw_output or "<empty model response>",
            timestamp=utc_now(),
            adapter_diagnostics=diagnostics,
        )

    def _request_json(self, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8")[:1_000]
            except OSError:
                detail = ""
            raise OllamaAdapterError(
                f"Local Ollama request failed: HTTP {exc.code}",
                {
                    "contract_version": OLLAMA_PROPOSAL_CONTRACT_V1,
                    "error": "adapter_or_network_error",
                    "http_status": exc.code,
                    "response_detail": detail,
                },
            ) from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaAdapterError(
                f"Local Ollama request failed: {exc}",
                {"contract_version": OLLAMA_PROPOSAL_CONTRACT_V1, "error": "adapter_or_network_error"},
            ) from exc
        if not isinstance(decoded, dict):
            raise OllamaAdapterError(
                "Local Ollama returned a non-object response",
                {"contract_version": OLLAMA_PROPOSAL_CONTRACT_V1, "error": "invalid_api_response"},
            )
        return decoded

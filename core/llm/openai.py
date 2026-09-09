"""OpenAI-compatible LLM adapter for Hermes' API Server.

Hermes Agent exposes an OpenAI-compatible HTTP API (the ``api_server`` gateway
adapter) on ``127.0.0.1:8642`` by default.  This provider talks that dialect so
ECON can use a running Hermes instance as its teacher/fallback LLM instead of a
standalone Ollama model.

Wire protocol: POST ``{base_url}/chat/completions`` with an OpenAI-style body
(``model``, ``messages``, ``stream: false``), authenticated with a bearer token.
The JSON schema for the structured reply is embedded in the system prompt (the
Hermes API server does not accept Ollama's ``format`` field nor a native
``response_format`` json_schema), and the returned ``message.content`` is parsed
back into a ``HermesProposal``.
"""

from __future__ import annotations

import json
import re

import httpx

from core.llm import HermesProposal, LLMResult, LLMUsage
from core.llm.ollama import LLMError
from core.secrets import redact, redact_mapping


_SYSTEM_PROMPT = (
    "You compile natural-language commands into ECON structured JSON. "
    "Never invent destructive commands. "
    "Never request or echo secrets, API keys, or tokens. "
    "Prefer argv over a single shell string. "
    "For HTTP actions set type to http and put url, method, body, "
    "and headers in extra; use env refs for secrets. "
    "When a remainder is a parameter (movie title, search query), "
    "put {query} in argv or extra instead of the literal value. "
    "Set triggers to the phrase prefixes that should replay this flow "
    "(without the parameter). "
    "Reply with JSON only."
)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class OpenAICompatibleProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_s: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def ping(self) -> bool:
        try:
            response = httpx.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=5.0,
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def generate_structured(self, payload: dict) -> LLMResult:
        schema = HermesProposal.model_json_schema()
        safe_payload = redact_mapping(payload)
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{_SYSTEM_PROMPT}\n"
                        f"Output must be valid JSON matching this schema:\n"
                        f"{json.dumps(schema)}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Compile this request into the JSON schema. Context: {safe_payload}"
                    ),
                },
            ],
            "stream": False,
            "temperature": 0,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers=self._headers(),
                timeout=self.timeout_s,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Hermes API unreachable at {self.base_url}: {exc}") from exc

        if response.status_code >= 400:
            raise LLMError(
                f"Hermes API HTTP {response.status_code}: {redact(response.text[:500])}"
            )

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise LLMError("Hermes API returned an unexpected response shape") from None

        content = _strip_fences(content)
        try:
            proposal = HermesProposal.model_validate_json(content)
        except Exception as exc:
            raise LLMError(f"Hermes returned invalid JSON: {exc}") from exc

        usage = data.get("usage") or {}
        return LLMResult(
            proposal=proposal,
            raw=data,
            usage=LLMUsage(
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
            ),
            model=data.get("model") or self.model,
        )


def _strip_fences(content: str) -> str:
    """Tolerate code-fenced JSON returned by models that ignore 'JSON only'."""
    match = _FENCE_RE.search(content)
    if match:
        return match.group(1).strip()
    return content.strip()

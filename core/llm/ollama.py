"""Ollama adapter. Hermes stays on the host; this never shells out.

Structured output: https://docs.ollama.com/capabilities/structured-outputs
Chat API: https://docs.ollama.com/api/chat
"""

from __future__ import annotations

import httpx

from core.llm import HermesProposal, LLMResult, LLMUsage


class LLMError(RuntimeError):
    pass


class OllamaProvider:
    def __init__(self, base_url: str, model: str, timeout_s: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def ping(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def generate_structured(self, payload: dict) -> LLMResult:
        schema = HermesProposal.model_json_schema()
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You compile natural-language commands into ECON structured JSON. "
                        "Never invent destructive commands. "
                        "Prefer argv over a single shell string. "
                        "Reply with JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": (f"Compile this request into the JSON schema. Context: {payload}"),
                },
            ],
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
        }
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=body,
                timeout=self.timeout_s,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama unreachable at {self.base_url}: {exc}") from exc

        if response.status_code >= 400:
            raise LLMError(f"Ollama HTTP {response.status_code}: {response.text[:500]}")

        data = response.json()
        content = (data.get("message") or {}).get("content") or ""
        try:
            proposal = HermesProposal.model_validate_json(content)
        except Exception as exc:
            raise LLMError(f"Hermes returned invalid JSON: {exc}") from exc

        return LLMResult(
            proposal=proposal,
            raw=data,
            usage=LLMUsage(
                prompt_tokens=int(data.get("prompt_eval_count") or 0),
                completion_tokens=int(data.get("eval_count") or 0),
            ),
            model=data.get("model") or self.model,
        )

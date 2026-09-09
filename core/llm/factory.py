"""LLM provider factory — selects Ollama or the Hermes OpenAI-compatible API.

``provider`` is the value of ``settings.ECON["LLM_PROVIDER"]``:
  * ``ollama`` (default) -> :class:`core.llm.ollama.OllamaProvider`
  * ``openai`` / ``hermes`` / ``openai-compatible`` -> :class:`core.llm.openai.OpenAICompatibleProvider`

The Hermes provider targets the Hermes Agent API Server (OpenAI-compatible) so
ECON can use a running Hermes instance as its teacher/fallback LLM.
"""

from __future__ import annotations

from typing import Any

from core.llm import LLMProvider
from core.llm.ollama import OllamaProvider
from core.llm.openai import OpenAICompatibleProvider

_OPENAI_ALIASES = {"openai", "openai-compatible", "hermes", "hermes-api", "api_server"}


def build_llm_provider(cfg: dict[str, Any]) -> LLMProvider:
    provider = str(cfg.get("LLM_PROVIDER", "ollama")).strip().lower()
    base_url = str(cfg.get("LLM_BASE_URL", "http://127.0.0.1:11434"))
    model = str(cfg.get("LLM_MODEL", "hermes"))
    if provider in _OPENAI_ALIASES:
        api_key = str(cfg.get("LLM_API_KEY", ""))
        return OpenAICompatibleProvider(base_url=base_url, model=model, api_key=api_key)
    return OllamaProvider(base_url=base_url, model=model)

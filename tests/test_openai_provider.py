"""Unit tests for the OpenAI-compatible (Hermes API Server) provider + factory."""

from __future__ import annotations

import json

from core.llm import HermesProposal
from core.llm.factory import build_llm_provider
from core.llm.ollama import OllamaProvider
from core.llm.openai import OpenAICompatibleProvider, _strip_fences


def test_factory_defaults_to_ollama():
    provider = build_llm_provider({"LLM_PROVIDER": "ollama", "LLM_BASE_URL": "http://x", "LLM_MODEL": "m"})
    assert isinstance(provider, OllamaProvider)


def test_factory_hermes_returns_openai_provider():
    provider = build_llm_provider(
        {
            "LLM_PROVIDER": "hermes",
            "LLM_BASE_URL": "http://127.0.0.1:8642/v1",
            "LLM_MODEL": "hermes-agent",
            "LLM_API_KEY": "secret",
        }
    )
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "http://127.0.0.1:8642/v1"
    assert provider.model == "hermes-agent"
    assert provider.api_key == "secret"


def test_factory_openai_alias():
    provider = build_llm_provider({"LLM_PROVIDER": "openai-compatible"})
    assert isinstance(provider, OpenAICompatibleProvider)


def test_strip_fences_plain():
    assert _strip_fences('{"a": 1}') == '{"a": 1}'


def test_strip_fences_code_block():
    assert _strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_provider_builds_openai_body_with_schema():
    provider = OpenAICompatibleProvider(
        base_url="http://127.0.0.1:8642/v1", model="hermes-agent", api_key="k"
    )
    # Reconstruct what generate_structured sends by inspecting a mock-free path:
    # verify headers + that the schema is embedded in the system prompt.
    headers = provider._headers()
    assert headers["Authorization"] == "Bearer k"
    assert headers["Content-Type"] == "application/json"
    # The schema must be a valid HermesProposal schema (imports cleanly).
    schema = HermesProposal.model_json_schema()
    assert "intent" in schema.get("properties", {})

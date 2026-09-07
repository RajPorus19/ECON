"""YAML configuration for ECON. Environment variables always win."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.config import env_float, env_int, env_str
from core.learning import DEFAULT_ALIAS_CONFIRMATIONS
from core.tokens import DEFAULT_ESTIMATED_BASELINE


@dataclass
class EconomConfig:
    llm_provider: str = "ollama"
    llm_model: str = "hermes"
    llm_base_url: str = "http://127.0.0.1:11434"
    confidence_threshold: float = 0.90
    alias_confirmations: int = DEFAULT_ALIAS_CONFIRMATIONS
    semantic_threshold: float = 0.82
    execution_timeout: int = 30
    execution_mode: str = "local"
    host_agent_url: str = "http://127.0.0.1:8765"
    host_agent_token: str = ""
    destructive_actions: str = "deny"
    filesystem_actions: str = "confirm"
    estimated_baseline_tokens: int = DEFAULT_ESTIMATED_BASELINE
    cache_ttl_seconds: int = 86400
    extra: dict[str, Any] = field(default_factory=dict)


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    inner = data.get("econom")
    return inner if isinstance(inner, dict) else data


def _nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def load_econom_config(path: Path | None = None) -> EconomConfig:
    yaml_data = load_yaml_file(path) if path else {}
    cfg = EconomConfig(
        llm_provider=str(_nested(yaml_data, "llm", "provider", default="ollama")),
        llm_model=str(_nested(yaml_data, "llm", "model", default="hermes")),
        llm_base_url=str(_nested(yaml_data, "llm", "base_url", default="http://127.0.0.1:11434")),
        confidence_threshold=float(
            _nested(yaml_data, "matching", "confidence_threshold", default=0.90)
        ),
        alias_confirmations=int(
            _nested(
                yaml_data,
                "matching",
                "alias_confirmations",
                default=DEFAULT_ALIAS_CONFIRMATIONS,
            )
        ),
        semantic_threshold=float(
            _nested(yaml_data, "matching", "semantic_threshold", default=0.82)
        ),
        execution_timeout=int(_nested(yaml_data, "execution", "default_timeout", default=30)),
        execution_mode=str(_nested(yaml_data, "execution", "mode", default="local")),
        host_agent_url=str(
            _nested(yaml_data, "execution", "host_agent_url", default="http://127.0.0.1:8765")
        ),
        destructive_actions=str(
            _nested(yaml_data, "security", "destructive_actions", default="deny")
        ),
        filesystem_actions=str(
            _nested(yaml_data, "security", "filesystem_actions", default="confirm")
        ),
        estimated_baseline_tokens=int(
            _nested(yaml_data, "tokens", "estimated_baseline", default=DEFAULT_ESTIMATED_BASELINE)
        ),
        cache_ttl_seconds=int(_nested(yaml_data, "cache", "ttl_seconds", default=86400)),
        extra=yaml_data,
    )
    # Env wins. Sources: STACK.md configuration + existing ECON_* variables.
    cfg.llm_model = env_str("ECON_LLM_MODEL", cfg.llm_model)
    cfg.llm_base_url = env_str("ECON_LLM_BASE_URL", cfg.llm_base_url)
    cfg.llm_provider = env_str("ECON_LLM_PROVIDER", cfg.llm_provider)
    cfg.confidence_threshold = env_float("ECON_CONFIDENCE_THRESHOLD", cfg.confidence_threshold)
    cfg.alias_confirmations = env_int("ECON_ALIAS_CONFIRMATIONS", cfg.alias_confirmations)
    cfg.semantic_threshold = env_float("ECON_SEMANTIC_THRESHOLD", cfg.semantic_threshold)
    cfg.execution_timeout = env_int("ECON_EXECUTION_TIMEOUT", cfg.execution_timeout)
    cfg.execution_mode = env_str("ECON_EXECUTION_MODE", cfg.execution_mode)
    cfg.host_agent_url = env_str("ECON_HOST_AGENT_URL", cfg.host_agent_url)
    cfg.host_agent_token = env_str("ECON_HOST_AGENT_TOKEN", cfg.host_agent_token)
    cfg.estimated_baseline_tokens = env_int(
        "ECON_ESTIMATED_BASELINE_TOKENS", cfg.estimated_baseline_tokens
    )
    cfg.cache_ttl_seconds = env_int("ECON_CACHE_TTL_SECONDS", cfg.cache_ttl_seconds)
    return cfg

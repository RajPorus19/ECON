"""Environment helpers used by Django settings and the CLI. No Django imports."""

from __future__ import annotations

import os


def env_str(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int = 0) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def env_float(name: str, default: float = 0.0) -> float:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]

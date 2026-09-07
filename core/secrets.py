"""Keep secrets out of flows, logs, and LLM prompts. Env vars are the MVP store."""

from __future__ import annotations

import os
import re

_SECRET_NAME_RE = re.compile(r"(API_KEY|TOKEN|PASSWORD|SECRET|CREDENTIAL|AUTH)", re.IGNORECASE)


def collect_secret_values(environ: dict[str, str] | None = None) -> list[str]:
    env = environ if environ is not None else dict(os.environ)
    values: list[str] = []
    for name, value in env.items():
        if not value or len(value) < 4:
            continue
        if _SECRET_NAME_RE.search(name):
            values.append(value)
    return values


def redact(text: str, secrets: list[str] | None = None) -> str:
    redacted = text
    for secret in secrets if secrets is not None else collect_secret_values():
        if secret:
            redacted = redacted.replace(secret, "***")
    return redacted


def redact_mapping(payload: dict, secrets: list[str] | None = None) -> dict:
    raw = str(payload)
    cleaned = redact(raw, secrets)
    if cleaned == raw:
        return payload
    # Best-effort: never return a structure that still contains a known secret.
    return {"redacted": True, "summary": cleaned[:2000]}


def resolve_env_refs(value: str, environ: dict[str, str] | None = None) -> str:
    """Resolve ${ENV_NAME} placeholders. Used by plugins; never logged."""
    env = environ if environ is not None else dict(os.environ)
    pattern = re.compile(r"\$\{([A-Z0-9_]+)\}")

    def repl(match: re.Match[str]) -> str:
        return env.get(match.group(1), "")

    return pattern.sub(repl, value)

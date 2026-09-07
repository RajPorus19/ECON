"""HTTP executor for provider/plugin actions. Never logs secret headers."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx

from core.execution import ExecuteRequest, ExecuteResult
from core.secrets import redact, resolve_env_refs


class HttpExecutor:
    def __init__(self, timeout_s: float = 30.0, client: httpx.Client | None = None) -> None:
        self.timeout_s = timeout_s
        self.client = client

    def execute(self, request: ExecuteRequest) -> ExecuteResult:
        extra = _resolve_env_tree(request.extra or {})
        url = extra.get("url") or (request.argv[1] if len(request.argv) > 1 else "")
        if not url:
            return ExecuteResult(success=False, error="http executor requires a url")
        method = (extra.get("method") or "GET").upper()
        headers = dict(extra.get("headers") or {}) if isinstance(extra.get("headers"), dict) else {}
        body = extra.get("body")
        timeout = request.timeout_s or self.timeout_s
        try:
            if self.client is not None:
                response = self.client.request(
                    method,
                    url,
                    headers=headers,
                    json=body if body is not None else None,
                    timeout=timeout,
                )
            else:
                response = httpx.request(
                    method,
                    url,
                    headers=headers,
                    json=body if body is not None else None,
                    timeout=timeout,
                )
        except httpx.HTTPError as exc:
            return ExecuteResult(success=False, error=redact(str(exc)))
        success = 200 <= response.status_code < 300
        return ExecuteResult(
            success=success,
            exit_code=response.status_code,
            stdout=response.text[:8000],
            error="" if success else redact(f"HTTP {response.status_code}"),
        )


def interpolate_command(template: list[str], parameters: dict[str, Any]) -> list[str]:
    return [interpolate_text(part, parameters) for part in template]


def interpolate_text(value: str, parameters: dict[str, Any]) -> str:
    rendered = value
    for key, raw in parameters.items():
        token = "{" + str(key) + "}"
        if token not in rendered:
            continue
        text = quote(str(raw), safe="") if key in {"query", "search"} else str(raw)
        rendered = rendered.replace(token, text)
    return rendered


def interpolate_mapping(value: Any, parameters: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return interpolate_text(value, parameters)
    if isinstance(value, dict):
        return {str(key): interpolate_mapping(item, parameters) for key, item in value.items()}
    if isinstance(value, list):
        return [interpolate_mapping(item, parameters) for item in value]
    return value


def json_bindings(stdout: str) -> dict[str, Any]:
    """Pull {item_id}/{session_id} out of Jellyfin-style JSON for the next step."""
    if not stdout or not stdout.strip():
        return {}
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    found: dict[str, Any] = {}
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and data[0].get("Id"):
            found["session_id"] = data[0]["Id"]
            found.setdefault("item_id", data[0]["Id"])
        return found
    if not isinstance(data, dict):
        return found
    items = data.get("Items")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        first = items[0]
        if first.get("Id"):
            found["item_id"] = first["Id"]
        if first.get("Name"):
            found["item_name"] = first["Name"]
    if data.get("Id"):
        found.setdefault("item_id", data["Id"])
        if data.get("SupportsRemoteControl"):
            found["session_id"] = data["Id"]
    sessions = data.get("Sessions")
    if isinstance(sessions, list) and sessions and isinstance(sessions[0], dict):
        if sessions[0].get("Id"):
            found["session_id"] = sessions[0]["Id"]
    return found


def _resolve_env_tree(value: Any) -> Any:
    if isinstance(value, str):
        return resolve_env_refs(value)
    if isinstance(value, dict):
        return {str(key): _resolve_env_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_env_tree(item) for item in value]
    return value

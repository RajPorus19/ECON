"""HTTP executor for provider/plugin actions. Never logs secret headers."""

from __future__ import annotations

from typing import Any

import httpx

from core.execution import ExecuteRequest, ExecuteResult
from core.secrets import redact


class HttpExecutor:
    def __init__(self, timeout_s: float = 30.0, client: httpx.Client | None = None) -> None:
        self.timeout_s = timeout_s
        self.client = client

    def execute(self, request: ExecuteRequest) -> ExecuteResult:
        extra = request.extra or {}
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
    rendered: list[str] = []
    for part in template:
        value = part
        for key, raw in parameters.items():
            value = value.replace("{" + str(key) + "}", str(raw))
        rendered.append(value)
    return rendered

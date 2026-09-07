"""Forward argv to the host-side agent when ECON runs in Docker."""

from __future__ import annotations

import httpx

from core.execution import ExecuteRequest, ExecuteResult


class HostAgentExecutor:
    def __init__(self, base_url: str, token: str, timeout_s: float = 35.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_s = timeout_s

    def execute(self, request: ExecuteRequest) -> ExecuteResult:
        try:
            response = httpx.post(
                f"{self.base_url}/v1/exec",
                json={
                    "argv": request.argv,
                    "timeout_s": request.timeout_s,
                    "cwd": request.cwd,
                },
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout_s,
            )
        except httpx.HTTPError as exc:
            return ExecuteResult(success=False, error=f"host agent unreachable: {exc}")

        if response.status_code == 401:
            return ExecuteResult(success=False, error="host agent rejected token")
        if response.status_code >= 400:
            return ExecuteResult(
                success=False,
                error=f"host agent HTTP {response.status_code}: {response.text[:500]}",
            )

        data = response.json()
        return ExecuteResult(
            success=bool(data.get("success")),
            exit_code=data.get("exit_code"),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            error=data.get("error", ""),
        )

    def ping(self) -> bool:
        try:
            response = httpx.get(
                f"{self.base_url}/v1/health",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=3.0,
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False

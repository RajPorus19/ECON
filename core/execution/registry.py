from __future__ import annotations

from core.execution import Executor
from core.execution.host_agent import HostAgentExecutor
from core.execution.http import HttpExecutor
from core.execution.local import LocalSubprocessExecutor


def executor_for(name: str, *, fallback: Executor | None = None) -> Executor:
    key = (name or "shell").lower()
    if key in {"shell", "process", "filesystem"}:
        return fallback or LocalSubprocessExecutor()
    if key == "http":
        return HttpExecutor()
    if key == "host_agent":
        if fallback is not None:
            return fallback
        raise ValueError("host_agent executor requires a configured HostAgentExecutor")
    return fallback or LocalSubprocessExecutor()


__all__ = ["HostAgentExecutor", "HttpExecutor", "LocalSubprocessExecutor", "executor_for"]

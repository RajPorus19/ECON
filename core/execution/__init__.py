from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ExecuteResult:
    success: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str = ""


@dataclass
class ExecuteRequest:
    argv: list[str]
    timeout_s: float = 30.0
    cwd: str | None = None
    extra: dict = field(default_factory=dict)


class Executor(Protocol):
    def execute(self, request: ExecuteRequest) -> ExecuteResult: ...


def ping_shell_executor() -> tuple[bool, str]:
    """Doctor helper: argv subprocess, never shell=True."""
    from core.execution.local import LocalSubprocessExecutor

    result = LocalSubprocessExecutor().execute(
        ExecuteRequest(argv=["echo", "econ-doctor"], timeout_s=5.0)
    )
    if result.success and "econ-doctor" in (result.stdout or ""):
        return True, "local subprocess"
    return False, result.error or "echo failed"

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
    extra: dict[str, str] = field(default_factory=dict)


class Executor(Protocol):
    def execute(self, request: ExecuteRequest) -> ExecuteResult: ...

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


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


@dataclass
class FlowStep:
    """One node in a walk: shell argv or HTTP extra payload."""

    executor: str = "shell"
    argv: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    security_level: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlowStep:
        return cls(
            executor=str(data.get("executor") or "shell"),
            argv=[str(part) for part in data.get("argv") or []],
            extra=dict(data.get("extra") or {}),
            security_level=data.get("security_level"),
        )


def normalize_steps(raw: Any) -> list[FlowStep]:
    if not raw:
        return []
    if isinstance(raw, list) and raw and isinstance(raw[0], str):
        return [FlowStep(executor="shell", argv=[str(part) for part in raw])]
    steps: list[FlowStep] = []
    for item in raw:
        if isinstance(item, FlowStep):
            steps.append(item)
        elif isinstance(item, dict):
            steps.append(FlowStep.from_dict(item))
    return steps


def flatten_argv(steps: list[FlowStep]) -> list[str]:
    for step in steps:
        if step.argv:
            return list(step.argv)
    return ["http"] if steps else []


def ping_shell_executor() -> tuple[bool, str]:
    """Doctor helper: argv subprocess, never shell=True."""
    from core.execution.local import LocalSubprocessExecutor

    result = LocalSubprocessExecutor().execute(
        ExecuteRequest(argv=["echo", "econ-doctor"], timeout_s=5.0)
    )
    if result.success and "econ-doctor" in (result.stdout or ""):
        return True, "local subprocess"
    return False, result.error or "echo failed"

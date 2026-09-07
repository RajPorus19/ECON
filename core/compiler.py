"""Compile a Hermes proposal into FlowSteps. Never execute it."""

from __future__ import annotations

import shlex

from core.execution import FlowStep, flatten_argv
from core.llm import ActionProposal, HermesProposal

_HTTP_TYPES = frozenset({"http", "http.request", "httpx"})


class CompileError(ValueError):
    pass


def argv_from_action(action: ActionProposal) -> list[str]:
    if action.argv:
        if not all(isinstance(part, str) and part for part in action.argv):
            raise CompileError("argv entries must be non-empty strings")
        return list(action.argv)
    if action.command:
        parts = shlex.split(action.command, posix=True)
        if not parts:
            raise CompileError("empty command")
        return parts
    raise CompileError("action has neither argv nor command")


def _extra_from_action(action: ActionProposal) -> dict:
    extra: dict = {}
    if action.parameters:
        extra.update(action.parameters)
    if action.extra:
        extra.update(action.extra)
    return extra


def _is_http(action: ActionProposal) -> bool:
    kind = (action.type or "").lower()
    if kind in _HTTP_TYPES:
        return True
    extra = _extra_from_action(action)
    return bool(extra.get("url"))


def compile_action(action: ActionProposal) -> FlowStep:
    extra = _extra_from_action(action)
    if _is_http(action):
        if action.command and "url" not in extra:
            extra["url"] = action.command
        argv = list(action.argv) if action.argv else ["http"]
        return FlowStep(executor="http", argv=argv, extra=extra, security_level=2)
    return FlowStep(executor="shell", argv=argv_from_action(action), extra=extra, security_level=1)


def compile_proposal(proposal: HermesProposal) -> list[FlowStep]:
    if not proposal.actions:
        raise CompileError("Hermes proposal contains no actions")
    return [compile_action(action) for action in proposal.actions]


def first_argv(proposal: HermesProposal) -> list[str]:
    argv = flatten_argv(compile_proposal(proposal))
    if not argv:
        raise CompileError("Hermes proposal contains no actions")
    return argv

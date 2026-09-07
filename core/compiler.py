"""Compile a Hermes proposal into argv. Never execute it."""

from __future__ import annotations

import shlex

from core.llm import ActionProposal, HermesProposal


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


def first_argv(proposal: HermesProposal) -> list[str]:
    if not proposal.actions:
        raise CompileError("Hermes proposal contains no actions")
    return argv_from_action(proposal.actions[0])

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
    argv = argv_from_action(action)
    # A single-token argv naming a provider action (e.g. "jellyfin.search",
    # "steam.launch") is resolved through the plugin, not run as a shell command.
    resolved = _resolve_provider_action(argv)
    if resolved is not None:
        return resolved
    return FlowStep(executor="shell", argv=argv, extra=extra, security_level=1)


def _resolve_provider_action(argv: list[str]) -> FlowStep | None:
    """Map a provider action name to the plugin's HTTP/shell FlowStep.

    The LLM compiles unknown requests by referencing provider action names
    (available in the prompt context) — but it has no way to know the
    provider's URL/headers, so the plugin owns that mapping.  Core stays
    unaware of provider specifics except through these lazy imports.
    """
    if len(argv) != 1:
        return None
    name = argv[0]
    if name.startswith("jellyfin."):
        from plugins.jellyfin import resolve_action

        return resolve_action(name)
    if name == "steam.launch":
        from plugins.steam import resolve_launch

        return resolve_launch()
    return None


def compile_proposal(proposal: HermesProposal) -> list[FlowStep]:
    if not proposal.actions:
        raise CompileError("Hermes proposal contains no actions")
    intent_name = (proposal.intent.name if proposal.intent else "").lower()
    commands = [str(a.command or "") for a in proposal.actions]
    # Media playback on Jellyfin must resolve the item first, then play it.
    # The LLM may emit only jellyfin.play (it can't know the item id); mirror
    # the stored-flow path and compose search → play.
    if intent_name == "play_media" and "jellyfin.play" in commands and "jellyfin.search" not in commands:
        from plugins.jellyfin import compose_play_steps

        return compose_play_steps(query="")
    return [compile_action(action) for action in proposal.actions]


def first_argv(proposal: HermesProposal) -> list[str]:
    argv = flatten_argv(compile_proposal(proposal))
    if not argv:
        raise CompileError("Hermes proposal contains no actions")
    return argv

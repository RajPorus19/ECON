"""Security policy for proposed actions. Hermes never reaches the shell directly."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum, StrEnum


class SecurityLevel(IntEnum):
    READ = 0
    LAUNCH = 1
    HTTP = 2
    FILESYSTEM = 3
    PROCESS_KILL = 4
    DESTRUCTIVE = 5


class Decision(StrEnum):
    AUTO = "auto"
    CONFIRM = "confirm"
    DENY = "deny"


_DENY_PATTERNS = (
    re.compile(r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f\s+/\s*$"),
    re.compile(r"rm\s+-[a-zA-Z]*f[a-zA-Z]*r\s+/\s*$"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bformat\b"),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\s*\}\s*;"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"\bdiskutil\s+erase"),
    re.compile(r"\bmkfs\."),
    re.compile(r">\s*/dev/sd"),
)


@dataclass(frozen=True)
class SecurityPolicy:
    launch: Decision = Decision.AUTO
    http: Decision = Decision.AUTO
    filesystem: Decision = Decision.CONFIRM
    process_kill: Decision = Decision.CONFIRM
    shutdown: Decision = Decision.CONFIRM
    destructive: Decision = Decision.DENY


@dataclass(frozen=True)
class SecurityVerdict:
    decision: Decision
    reason: str
    level: SecurityLevel


def infer_level(argv: list[str], explicit: int | None = None) -> SecurityLevel:
    if explicit is not None:
        return SecurityLevel(explicit)
    if not argv:
        return SecurityLevel.READ
    binary = argv[0].rsplit("/", 1)[-1].lower()
    if binary in {"mkfs", "dd", "format", "diskutil"}:
        return SecurityLevel.DESTRUCTIVE
    if binary in {"shutdown", "reboot", "halt", "poweroff"}:
        return SecurityLevel.DESTRUCTIVE
    if binary in {"kill", "killall", "pkill"}:
        return SecurityLevel.PROCESS_KILL
    if binary in {"rm", "mv", "cp", "chmod", "chown", "rmdir", "unlink", "trash"}:
        return SecurityLevel.FILESYSTEM
    if binary in {"curl", "wget", "http"}:
        return SecurityLevel.HTTP
    return SecurityLevel.LAUNCH


def _joined(argv: list[str]) -> str:
    return " ".join(argv)


def _decision_for_level(level: SecurityLevel, policy: SecurityPolicy) -> Decision:
    if level is SecurityLevel.DESTRUCTIVE:
        return policy.destructive
    if level is SecurityLevel.PROCESS_KILL:
        return policy.process_kill
    if level is SecurityLevel.FILESYSTEM:
        return policy.filesystem
    if level is SecurityLevel.HTTP:
        return policy.http
    return policy.launch


def evaluate(
    argv: list[str],
    *,
    level: SecurityLevel | None = None,
    confirmed: bool = False,
    policy: SecurityPolicy | None = None,
) -> SecurityVerdict:
    rules = policy or SecurityPolicy()
    if not argv:
        return SecurityVerdict(Decision.DENY, "empty command", SecurityLevel.READ)

    joined = _joined(argv)
    for pattern in _DENY_PATTERNS:
        if pattern.search(joined):
            return SecurityVerdict(
                Decision.DENY, "destructive pattern blocked", SecurityLevel.DESTRUCTIVE
            )

    resolved = level or infer_level(argv)
    binary = argv[0].rsplit("/", 1)[-1].lower()
    if binary in {"shutdown", "reboot", "halt", "poweroff"}:
        decision = rules.shutdown
        if decision is Decision.DENY:
            return SecurityVerdict(Decision.DENY, "system action denied", resolved)
        if decision is Decision.CONFIRM and not confirmed:
            return SecurityVerdict(
                Decision.CONFIRM, "system action requires confirmation", resolved
            )
        return SecurityVerdict(Decision.AUTO, "confirmed system action", resolved)

    decision = _decision_for_level(resolved, rules)
    if decision is Decision.DENY:
        return SecurityVerdict(Decision.DENY, f"{resolved.name.lower()} action denied", resolved)
    if decision is Decision.CONFIRM and not confirmed:
        return SecurityVerdict(
            Decision.CONFIRM,
            f"{resolved.name.lower()} action requires confirmation",
            resolved,
        )
    if decision is Decision.CONFIRM and confirmed:
        return SecurityVerdict(Decision.AUTO, "confirmed action", resolved)
    return SecurityVerdict(Decision.AUTO, "allowed", resolved)


def policy_from_mapping(data: dict[str, str] | None) -> SecurityPolicy:
    data = data or {}

    def parse(key: str, default: Decision) -> Decision:
        raw = str(data.get(key, default.value)).lower()
        try:
            return Decision(raw)
        except ValueError:
            return default

    return SecurityPolicy(
        launch=parse("launch", Decision.AUTO),
        http=parse("http", Decision.AUTO),
        filesystem=parse("filesystem_actions", Decision.CONFIRM),
        process_kill=parse("process_kill", Decision.CONFIRM),
        shutdown=parse("shutdown", Decision.CONFIRM),
        destructive=parse("destructive_actions", Decision.DENY),
    )

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


def evaluate(
    argv: list[str], *, level: SecurityLevel | None = None, confirmed: bool = False
) -> SecurityVerdict:
    if not argv:
        return SecurityVerdict(Decision.DENY, "empty command", SecurityLevel.READ)

    joined = _joined(argv)
    for pattern in _DENY_PATTERNS:
        if pattern.search(joined):
            return SecurityVerdict(
                Decision.DENY, "destructive pattern blocked", SecurityLevel.DESTRUCTIVE
            )

    resolved = level or infer_level(argv)
    if resolved >= SecurityLevel.DESTRUCTIVE:
        binary = argv[0].rsplit("/", 1)[-1].lower()
        if binary in {"shutdown", "reboot", "halt", "poweroff"}:
            if confirmed:
                return SecurityVerdict(Decision.AUTO, "confirmed system action", resolved)
            return SecurityVerdict(
                Decision.CONFIRM, "system action requires confirmation", resolved
            )
        return SecurityVerdict(Decision.DENY, "destructive action denied", resolved)

    if resolved >= SecurityLevel.FILESYSTEM:
        if confirmed:
            return SecurityVerdict(Decision.AUTO, "confirmed filesystem/process action", resolved)
        return SecurityVerdict(
            Decision.CONFIRM, "filesystem/process action requires confirmation", resolved
        )

    return SecurityVerdict(Decision.AUTO, "allowed", resolved)

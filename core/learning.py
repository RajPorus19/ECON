"""Pure learning helpers. Alias promotion requires repeated confirmations."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_ALIAS_CONFIRMATIONS = 3


@dataclass(frozen=True)
class AliasObservation:
    normalized_phrase: str
    entity_name: str
    confirmations: int


def should_promote_alias(
    confirmations: int, *, required: int = DEFAULT_ALIAS_CONFIRMATIONS
) -> bool:
    """Do not create an alias after a single ambiguous use."""
    return confirmations >= required


def next_confirmation_count(current: int, *, matched_ambiguously: bool, success: bool) -> int:
    if not matched_ambiguously:
        return current
    if success:
        return current + 1
    return max(0, current - 1)

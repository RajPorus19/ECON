"""Deterministic matching helpers. No LLM involved."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AliasHit:
    key: str
    name: str
    confidence: float
    remainder: str


def longest_prefix_match(normalized: str, aliases: list[tuple[str, str, float]]) -> AliasHit | None:
    """aliases: (normalized_phrase, canonical_name, confidence)."""
    best: AliasHit | None = None
    for phrase, name, confidence in aliases:
        if not phrase:
            continue
        if normalized == phrase or normalized.startswith(phrase + " "):
            remainder = normalized[len(phrase) :].strip()
            if best is None or len(phrase) > len(best.key):
                best = AliasHit(phrase, name, confidence, remainder)
    return best


def exact_or_alias_match(token: str, names: list[tuple[str, str, float]]) -> AliasHit | None:
    """names: (normalized_name, canonical_name, confidence)."""
    if not token:
        return None
    for normalized_name, name, confidence in names:
        if token == normalized_name:
            return AliasHit(normalized_name, name, confidence, "")
    return None

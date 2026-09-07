"""Deterministic matching helpers. No LLM involved.

Pipeline: exact → normalized/alias → prefix → fuzzy → semantic.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from core.embeddings import EmbeddingBackend, NullEmbeddingBackend


@dataclass(frozen=True)
class AliasHit:
    key: str
    name: str
    confidence: float
    remainder: str
    method: str = "exact"


def longest_prefix_match(normalized: str, aliases: list[tuple[str, str, float]]) -> AliasHit | None:
    """aliases: (normalized_phrase, canonical_name, confidence)."""
    best: AliasHit | None = None
    for phrase, name, confidence in aliases:
        if not phrase:
            continue
        if normalized == phrase or normalized.startswith(phrase + " "):
            remainder = normalized[len(phrase) :].strip()
            if best is None or len(phrase) > len(best.key):
                method = "exact" if remainder == "" and normalized == phrase else "prefix"
                if normalized == phrase:
                    method = "exact"
                best = AliasHit(phrase, name, confidence, remainder, method)
    return best


def exact_or_alias_match(token: str, names: list[tuple[str, str, float]]) -> AliasHit | None:
    """names: (normalized_name, canonical_name, confidence)."""
    if not token:
        return None
    for normalized_name, name, confidence in names:
        if token == normalized_name:
            return AliasHit(normalized_name, name, confidence, "", "exact")
    return None


def fuzzy_match(
    token: str,
    names: list[tuple[str, str, float]],
    *,
    threshold: float = 0.86,
) -> AliasHit | None:
    if not token:
        return None
    best: AliasHit | None = None
    for normalized_name, name, confidence in names:
        if not normalized_name:
            continue
        ratio = SequenceMatcher(None, token, normalized_name).ratio()
        score = ratio * float(confidence)
        if ratio >= threshold and (best is None or score > best.confidence):
            best = AliasHit(normalized_name, name, score, "", "fuzzy")
    return best


def semantic_match(
    token: str,
    names: list[tuple[str, str, float]],
    embedder: EmbeddingBackend,
    *,
    threshold: float = 0.82,
) -> AliasHit | None:
    if not token or isinstance(embedder, NullEmbeddingBackend):
        return None
    query = embedder.embed(token)
    best: AliasHit | None = None
    for normalized_name, name, confidence in names:
        if not normalized_name:
            continue
        score = embedder.similarity(query, embedder.embed(normalized_name)) * float(confidence)
        if score >= threshold and (best is None or score > best.confidence):
            best = AliasHit(normalized_name, name, score, "", "semantic")
    return best


def match_entity(
    token: str,
    names: list[tuple[str, str, float]],
    *,
    embedder: EmbeddingBackend | None = None,
    semantic_threshold: float = 0.82,
) -> AliasHit | None:
    hit = exact_or_alias_match(token, names)
    if hit:
        return hit
    hit = longest_prefix_match(token, names)
    if hit:
        return hit
    hit = fuzzy_match(token, names)
    if hit:
        return hit
    if embedder is not None:
        return semantic_match(token, names, embedder, threshold=semantic_threshold)
    return None

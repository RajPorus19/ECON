"""Normalize user utterances before matching."""

from __future__ import annotations

import re
import unicodedata

FILLER_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "please",
        "me",
        "moi",
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "du",
        "de",
        "s'il",
        "sil",
        "te",
        "vous",
        "plaît",
        "plait",
        "just",
        "can",
        "you",
        "could",
        "stp",
        "svp",
    }
)

WAKE_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("hey", "hermes"),
    ("hey", "econ"),
    ("hermes",),
    ("econ",),
)

_PUNCT_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def strip_wake_tokens(tokens: list[str]) -> list[str]:
    """Drop a leading wake word (hermes / econ), including 'hey hermes'."""
    for prefix in WAKE_PREFIXES:
        n = len(prefix)
        if tuple(tokens[:n]) == prefix:
            return tokens[n:]
    return tokens


def normalize(text: str) -> str:
    """Lowercase, strip accents/punctuation, drop filler and wake words, collapse space."""
    without_apostrophe = text.replace("'", "").replace("’", "")
    lowered = strip_accents(without_apostrophe).lower().replace("-", " ")
    without_punct = _PUNCT_RE.sub(" ", lowered)
    tokens = [
        tok for tok in _SPACE_RE.split(without_punct.strip()) if tok and tok not in FILLER_WORDS
    ]
    tokens = strip_wake_tokens(tokens)
    return " ".join(tokens)


_WORD_RE = re.compile(r"[\w'-]+", re.UNICODE)


def original_span(text: str, normalized_span: str) -> str:
    """Shortest original-text suffix whose normalize() equals normalized_span."""
    if not text or not normalized_span:
        return normalized_span
    tokens = _WORD_RE.findall(text)
    best = normalized_span
    for index in range(len(tokens)):
        chunk = " ".join(tokens[index:])
        if normalize(chunk) == normalized_span:
            best = chunk
    return best

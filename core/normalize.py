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

_PUNCT_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize(text: str) -> str:
    """Lowercase, strip accents/punctuation, drop filler words, collapse space."""
    without_apostrophe = text.replace("'", "").replace("’", "")
    lowered = strip_accents(without_apostrophe).lower().replace("-", " ")
    without_punct = _PUNCT_RE.sub(" ", lowered)
    tokens = [
        tok for tok in _SPACE_RE.split(without_punct.strip()) if tok and tok not in FILLER_WORDS
    ]
    return " ".join(tokens)

"""Local embeddings interface. Vector DB is not required.

Swap HashEmbeddingBackend for a sentence-transformers (or similar) backend later.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol


class EmbeddingBackend(Protocol):
    def embed(self, text: str) -> list[float]: ...

    def similarity(self, left: list[float], right: list[float]) -> float: ...


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_l = math.sqrt(sum(a * a for a in left))
    norm_r = math.sqrt(sum(b * b for b in right))
    if norm_l == 0 or norm_r == 0:
        return 0.0
    return dot / (norm_l * norm_r)


class HashEmbeddingBackend:
    """Deterministic character n-gram hashing. Good enough as a stub for tests and MVP."""

    def __init__(self, dimensions: int = 64, ngram: int = 3) -> None:
        self.dimensions = dimensions
        self.ngram = ngram

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        padded = f" {text.lower()} "
        if len(padded) < self.ngram:
            return vector
        for i in range(len(padded) - self.ngram + 1):
            gram = padded[i : i + self.ngram]
            digest = hashlib.sha256(gram.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        return vector

    def similarity(self, left: list[float], right: list[float]) -> float:
        return cosine_similarity(left, right)


class NullEmbeddingBackend:
    def embed(self, text: str) -> list[float]:
        return []

    def similarity(self, left: list[float], right: list[float]) -> float:
        return 0.0

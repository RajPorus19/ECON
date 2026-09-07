"""Confidence scoring. Each matching step produces a score; the final score is the min."""

from __future__ import annotations

SUCCESS_DELTA = 0.02
FAILURE_DELTA = -0.10
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0


def clamp(value: float) -> float:
    return max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, value))


def combined_confidence(*scores: float) -> float:
    """Final score is the minimum of positive step scores (conservative)."""
    present = [float(score) for score in scores if score and score > 0]
    if not present:
        return 0.0
    return min(present)


def apply_outcome(current: float, *, success: bool) -> float:
    delta = SUCCESS_DELTA if success else FAILURE_DELTA
    return clamp(current + delta)


def meets_threshold(score: float, threshold: float) -> bool:
    return score >= threshold

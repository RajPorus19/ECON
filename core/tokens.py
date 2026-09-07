"""Estimated token savings. Baseline is not actually executed."""

from __future__ import annotations

DEFAULT_ESTIMATED_BASELINE = 1200


def estimated_tokens_saved(
    *,
    llm_used: bool,
    actual_tokens: int,
    baseline: int = DEFAULT_ESTIMATED_BASELINE,
) -> tuple[int, int]:
    """Return (estimated_tokens_without_econ, tokens_saved)."""
    estimated_without = baseline if not llm_used else max(baseline, actual_tokens)
    if llm_used:
        saved = max(0, estimated_without - actual_tokens)
    else:
        saved = estimated_without
    return estimated_without, saved

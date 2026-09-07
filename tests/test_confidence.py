from core.confidence import apply_outcome, combined_confidence, meets_threshold


def test_combined_is_minimum() -> None:
    assert combined_confidence(0.99, 1.0, 0.98, 0.99) == 0.98


def test_empty_combined_is_zero() -> None:
    assert combined_confidence() == 0.0
    assert combined_confidence(0, 0.0) == 0.0


def test_success_and_failure_deltas() -> None:
    assert apply_outcome(0.90, success=True) == 0.92
    assert apply_outcome(0.90, success=False) == 0.80


def test_clamp() -> None:
    assert apply_outcome(0.99, success=True) == 1.0
    assert apply_outcome(0.05, success=False) == 0.0


def test_threshold() -> None:
    assert meets_threshold(0.90, 0.90)
    assert not meets_threshold(0.89, 0.90)

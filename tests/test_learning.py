from core.learning import next_confirmation_count, should_promote_alias


def test_does_not_promote_after_one_use() -> None:
    assert should_promote_alias(1) is False
    assert should_promote_alias(2) is False
    assert should_promote_alias(3) is True


def test_confirmation_counter() -> None:
    assert next_confirmation_count(0, matched_ambiguously=True, success=True) == 1
    assert next_confirmation_count(2, matched_ambiguously=True, success=True) == 3
    assert next_confirmation_count(2, matched_ambiguously=False, success=True) == 2
    assert next_confirmation_count(1, matched_ambiguously=True, success=False) == 0

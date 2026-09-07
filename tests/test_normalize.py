from core.normalize import normalize


def test_normalize_strips_accents_and_fillers() -> None:
    assert normalize("Lance-moi Sonic Crossworlds, s'il te plaît !") == "lance sonic crossworlds"


def test_normalize_collapses_space() -> None:
    assert normalize("  Start   Firefox  ") == "start firefox"


def test_normalize_strips_wake_word() -> None:
    assert normalize("hermes update the pc") == "update pc"
    assert normalize("hey hermes find me Dune") == "find dune"
    assert normalize("econ update the pc") == "update pc"


def test_original_span_keeps_title_case() -> None:
    from core.normalize import original_span

    assert original_span("find me Inception", "inception") == "Inception"

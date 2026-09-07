from core.normalize import normalize


def test_normalize_strips_accents_and_fillers() -> None:
    assert normalize("Lance-moi Sonic Crossworlds, s'il te plaît !") == "lance sonic crossworlds"


def test_normalize_collapses_space() -> None:
    assert normalize("  Start   Firefox  ") == "start firefox"

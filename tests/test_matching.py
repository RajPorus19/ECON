from core.matching import exact_or_alias_match, fuzzy_match, longest_prefix_match


def test_longest_prefix_prefers_longer_phrase() -> None:
    aliases = [
        ("lance", "launch_program", 0.9),
        ("lance sonic", "launch_program", 0.5),
    ]
    hit = longest_prefix_match("lance sonic crossworlds", aliases)
    assert hit is not None
    assert hit.key == "lance sonic"
    assert hit.remainder == "crossworlds"


def test_entity_exact_match() -> None:
    hit = exact_or_alias_match(
        "firefox",
        [("firefox", "Firefox", 1.0), ("sonic crossworlds", "Sonic Crossworlds", 1.0)],
    )
    assert hit is not None
    assert hit.name == "Firefox"


def test_fuzzy_close_token() -> None:
    hit = fuzzy_match("firef0x", [("firefox", "Firefox", 1.0)], threshold=0.7)
    assert hit is not None
    assert hit.name == "Firefox"
    assert hit.method == "fuzzy"

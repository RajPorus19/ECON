from pathlib import Path

from core.plugins import discover_manifests


def test_discovers_steam_and_jellyfin() -> None:
    root = Path(__file__).resolve().parent.parent / "plugins"
    manifests = {item.name: item for item in discover_manifests(root)}
    assert "steam" in manifests
    assert "jellyfin" in manifests
    assert "steam.launch" in manifests["steam"].action_ids()
    assert "play" in manifests["jellyfin"].capabilities


def test_steam_resolves_app_id_from_metadata() -> None:
    from plugins.steam import resolve_launch

    step = resolve_launch(metadata={"app_id": "440"}, entity_name="Team Fortress 2")
    assert step.argv == ["steam", "steam://rungameid/440"]


def test_jellyfin_compose_search_then_play(monkeypatch) -> None:
    monkeypatch.setenv("JELLYFIN_URL", "http://jelly.test")
    monkeypatch.setenv("JELLYFIN_API_KEY", "secret-key")
    monkeypatch.setenv("JELLYFIN_SESSION_ID", "sess-1")
    from plugins.jellyfin import compose_play_steps

    steps = compose_play_steps(query="Rick and Morty")
    assert len(steps) == 2
    assert steps[0].executor == "http"
    assert "Items" in steps[0].extra["url"]
    assert "searchTerm" in steps[0].extra["url"]
    assert "Playing" in steps[1].extra["url"]
    assert "${JELLYFIN_API_KEY}" in steps[0].extra["headers"]["X-Emby-Token"]
    assert "secret-key" not in str(steps[0].extra)

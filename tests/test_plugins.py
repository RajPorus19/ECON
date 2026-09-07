from pathlib import Path

from core.plugins import discover_manifests


def test_discovers_steam_and_jellyfin() -> None:
    root = Path(__file__).resolve().parent.parent / "plugins"
    manifests = {item.name: item for item in discover_manifests(root)}
    assert "steam" in manifests
    assert "jellyfin" in manifests
    assert "steam.launch" in manifests["steam"].action_ids()
    assert "play" in manifests["jellyfin"].capabilities

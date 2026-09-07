"""Steam provider plugin. Declares game launch capability; no secrets in manifests."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.execution import FlowStep
from core.execution.http import interpolate_command
from core.providers import ProviderDescriptor

STEAM_LAUNCH = ["steam", "steam://rungameid/{app_id}"]


class SteamProvider:
    name = "Steam"
    provider_type = "game_store"

    def capabilities(self) -> list[str]:
        return ["launch"]

    def actions(self) -> list[str]:
        return ["steam.launch"]

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            name=self.name,
            type=self.provider_type,
            capabilities=self.capabilities(),
            actions=self.actions(),
        )


def resolve_app_id(metadata: dict[str, Any] | None, entity_name: str = "") -> str:
    meta = metadata or {}
    for key in ("app_id", "steam_app_id", "appid"):
        value = meta.get(key)
        if value:
            return str(value)
    return lookup_app_id(entity_name) or ""


def lookup_app_id(entity_name: str) -> str | None:
    """Optional library lookup when STEAM_API_KEY (and STEAM_ID) are present."""
    key = os.environ.get("STEAM_API_KEY", "").strip()
    steam_id = os.environ.get("STEAM_ID", "").strip()
    if not key or not steam_id or not entity_name:
        return None
    try:
        response = httpx.get(
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/",
            params={"key": key, "steamid": steam_id, "include_appinfo": 1, "format": "json"},
            timeout=10.0,
        )
        response.raise_for_status()
        games = (((response.json() or {}).get("response") or {}).get("games")) or []
    except Exception:  # noqa: BLE001 — lookup is optional
        return None
    needle = entity_name.strip().lower()
    for game in games:
        if str(game.get("name", "")).strip().lower() == needle:
            app_id = game.get("appid")
            return str(app_id) if app_id is not None else None
    return None


def resolve_launch(*, metadata: dict[str, Any] | None = None, entity_name: str = "") -> FlowStep:
    app_id = resolve_app_id(metadata, entity_name)
    argv = interpolate_command(STEAM_LAUNCH, {"app_id": app_id or "{app_id}"})
    return FlowStep(executor="shell", argv=argv, security_level=1)

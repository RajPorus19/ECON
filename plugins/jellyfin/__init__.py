"""Jellyfin provider plugin. Credentials come from env, never from flows or prompts."""

from __future__ import annotations

import os
from typing import Any

from core.execution import FlowStep
from core.providers import ProviderDescriptor


class JellyfinProvider:
    name = "Jellyfin"
    provider_type = "media_server"

    def capabilities(self) -> list[str]:
        return ["search", "play", "pause", "stop"]

    def actions(self) -> list[str]:
        return ["jellyfin.search", "jellyfin.play", "jellyfin.pause", "jellyfin.stop"]

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            name=self.name,
            type=self.provider_type,
            capabilities=self.capabilities(),
            actions=self.actions(),
            config={"url_env": "JELLYFIN_URL", "api_key_env": "JELLYFIN_API_KEY"},
        )


def _base_url() -> str:
    return os.environ.get("JELLYFIN_URL", "").rstrip("/")


def _token_header() -> dict[str, str]:
    return {"X-Emby-Token": "${JELLYFIN_API_KEY}"}


def resolve_action(
    action_id: str,
    *,
    query: str = "",
    metadata: dict[str, Any] | None = None,
) -> FlowStep:
    """Build an HTTP step. API key stays an env ref until HttpExecutor resolves it."""
    base = _base_url()
    meta = metadata or {}
    item_id = str(meta.get("item_id") or "{item_id}")
    session_id = os.environ.get("JELLYFIN_SESSION_ID") or "{session_id}"
    headers = _token_header()
    extra: dict[str, Any]
    if action_id == "jellyfin.search":
        extra = {
            "url": f"{base}/Items?searchTerm={{query}}&Recursive=true&Limit=1",
            "method": "GET",
            "headers": headers,
        }
        return FlowStep(executor="http", argv=["http"], extra=extra, security_level=2)
    if action_id == "jellyfin.play":
        extra = {
            "url": (f"{base}/Sessions/{session_id}/Playing?ItemIds={item_id}&PlayCommand=PlayNow"),
            "method": "POST",
            "headers": headers,
        }
        return FlowStep(executor="http", argv=["http"], extra=extra, security_level=2)
    if action_id == "jellyfin.pause":
        extra = {
            "url": f"{base}/Sessions/{session_id}/Playing/Pause",
            "method": "POST",
            "headers": headers,
        }
        return FlowStep(executor="http", argv=["http"], extra=extra, security_level=2)
    if action_id == "jellyfin.stop":
        extra = {
            "url": f"{base}/Sessions/{session_id}/Playing/Stop",
            "method": "POST",
            "headers": headers,
        }
        return FlowStep(executor="http", argv=["http"], extra=extra, security_level=2)
    extra = {"url": base, "method": "GET", "headers": headers}
    return FlowStep(executor="http", argv=["http"], extra=extra, security_level=2)


def compose_play_steps(*, query: str, metadata: dict[str, Any] | None = None) -> list[FlowStep]:
    """play_media → jellyfin.search then jellyfin.play (SPECS §61)."""
    return [
        resolve_action("jellyfin.search", query=query, metadata=metadata),
        resolve_action("jellyfin.play", query=query, metadata=metadata),
    ]

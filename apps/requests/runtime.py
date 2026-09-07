"""Redis / memory phrase cache factory and event fan-out."""

from __future__ import annotations

import json
from typing import Any

from django.conf import settings

from core.cache import MemoryPhraseCache, PhraseCache, RedisPhraseCache
from core.events import EVENT_CHANNEL, EventBus

_memory = MemoryPhraseCache()


def get_phrase_cache() -> PhraseCache:
    backend = str(settings.ECON.get("CACHE_BACKEND", "memory"))
    if backend == "memory":
        return _memory
    try:
        import redis

        client = redis.from_url(
            str(settings.ECON.get("REDIS_URL") or settings.CELERY_RESULT_BACKEND)
        )
        client.ping()
        return RedisPhraseCache(
            client,
            ttl_seconds=int(str(settings.ECON.get("CACHE_TTL_SECONDS", 86400))),
        )
    except Exception:  # noqa: BLE001 — tests and offline doctor still work
        return _memory


def publish_event(event: str, payload: dict[str, Any] | None = None) -> None:
    message = json.dumps({"event": event, "payload": payload or {}})
    try:
        import redis

        url = str(settings.ECON.get("REDIS_URL") or getattr(settings, "CELERY_RESULT_BACKEND", ""))
        if not url:
            return
        client = redis.from_url(url)
        client.publish(EVENT_CHANNEL, message)
    except Exception:  # noqa: BLE001
        return


def bus_with_redis() -> EventBus:
    bus = EventBus()
    bus.subscribe("*", lambda event, payload: publish_event(event, payload))
    return bus

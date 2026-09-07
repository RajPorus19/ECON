"""Phrase cache layers: L1 exact → L2 normalized → L3 intent/entity → L4 flow."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass
class CachedResolution:
    intent_name: str | None = None
    entity_name: str | None = None
    provider_name: str | None = None
    flow_id: str | None = None
    flow_confidence: float = 0.0
    argv: list[str] = field(default_factory=list)
    layer: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> CachedResolution:
        data = json.loads(raw)
        return cls(**data)


class PhraseCache(Protocol):
    def get_exact(self, phrase: str) -> CachedResolution | None: ...

    def get_normalized(self, normalized: str) -> CachedResolution | None: ...

    def get_intent_entity(self, intent: str, entity: str | None) -> CachedResolution | None: ...

    def get_flow(self, flow_id: str) -> CachedResolution | None: ...

    def put_exact(self, phrase: str, value: CachedResolution) -> None: ...

    def put_normalized(self, normalized: str, value: CachedResolution) -> None: ...

    def put_intent_entity(
        self, intent: str, entity: str | None, value: CachedResolution
    ) -> None: ...

    def put_flow(self, flow_id: str, value: CachedResolution) -> None: ...

    def invalidate_flow(self, flow_id: str) -> None: ...


def _intent_entity_key(intent: str, entity: str | None) -> str:
    return f"{intent}|{entity or ''}"


class MemoryPhraseCache:
    """In-process cache used by tests and as a Redis fallback."""

    def __init__(self) -> None:
        self._exact: dict[str, CachedResolution] = {}
        self._normalized: dict[str, CachedResolution] = {}
        self._intent_entity: dict[str, CachedResolution] = {}
        self._flow: dict[str, CachedResolution] = {}

    def get_exact(self, phrase: str) -> CachedResolution | None:
        hit = self._exact.get(phrase)
        return _with_layer(hit, "L1")

    def get_normalized(self, normalized: str) -> CachedResolution | None:
        hit = self._normalized.get(normalized)
        return _with_layer(hit, "L2")

    def get_intent_entity(self, intent: str, entity: str | None) -> CachedResolution | None:
        hit = self._intent_entity.get(_intent_entity_key(intent, entity))
        return _with_layer(hit, "L3")

    def get_flow(self, flow_id: str) -> CachedResolution | None:
        hit = self._flow.get(flow_id)
        return _with_layer(hit, "L4")

    def put_exact(self, phrase: str, value: CachedResolution) -> None:
        self._exact[phrase] = value

    def put_normalized(self, normalized: str, value: CachedResolution) -> None:
        self._normalized[normalized] = value

    def put_intent_entity(self, intent: str, entity: str | None, value: CachedResolution) -> None:
        self._intent_entity[_intent_entity_key(intent, entity)] = value

    def put_flow(self, flow_id: str, value: CachedResolution) -> None:
        self._flow[flow_id] = value

    def invalidate_flow(self, flow_id: str) -> None:
        self._flow.pop(flow_id, None)
        self._exact = {k: v for k, v in self._exact.items() if v.flow_id != flow_id}
        self._normalized = {k: v for k, v in self._normalized.items() if v.flow_id != flow_id}
        self._intent_entity = {k: v for k, v in self._intent_entity.items() if v.flow_id != flow_id}


class RedisPhraseCache:
    """Redis-backed cache. Keys: econ:l1:, econ:l2:, econ:l3:, econ:l4:."""

    def __init__(self, client: Any, *, ttl_seconds: int = 86400, prefix: str = "econ") -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds
        self.prefix = prefix

    def _key(self, layer: str, suffix: str) -> str:
        return f"{self.prefix}:{layer}:{suffix}"

    def _get(self, key: str, layer: str) -> CachedResolution | None:
        raw = self.client.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        hit = CachedResolution.from_json(raw)
        return _with_layer(hit, layer)

    def _put(self, key: str, value: CachedResolution) -> None:
        self.client.set(key, value.to_json(), ex=self.ttl_seconds)

    def get_exact(self, phrase: str) -> CachedResolution | None:
        return self._get(self._key("l1", phrase), "L1")

    def get_normalized(self, normalized: str) -> CachedResolution | None:
        return self._get(self._key("l2", normalized), "L2")

    def get_intent_entity(self, intent: str, entity: str | None) -> CachedResolution | None:
        return self._get(self._key("l3", _intent_entity_key(intent, entity)), "L3")

    def get_flow(self, flow_id: str) -> CachedResolution | None:
        return self._get(self._key("l4", flow_id), "L4")

    def put_exact(self, phrase: str, value: CachedResolution) -> None:
        self._put(self._key("l1", phrase), value)

    def put_normalized(self, normalized: str, value: CachedResolution) -> None:
        self._put(self._key("l2", normalized), value)

    def put_intent_entity(self, intent: str, entity: str | None, value: CachedResolution) -> None:
        self._put(self._key("l3", _intent_entity_key(intent, entity)), value)

    def put_flow(self, flow_id: str, value: CachedResolution) -> None:
        self._put(self._key("l4", flow_id), value)

    def invalidate_flow(self, flow_id: str) -> None:
        self.client.delete(self._key("l4", flow_id))


def _with_layer(hit: CachedResolution | None, layer: str) -> CachedResolution | None:
    if hit is None:
        return None
    hit.layer = layer
    return hit


def lookup_layers(
    cache: PhraseCache,
    *,
    phrase: str,
    normalized: str,
    intent: str | None = None,
    entity: str | None = None,
    flow_id: str | None = None,
) -> CachedResolution | None:
    hit = cache.get_exact(phrase)
    if hit and hit.argv:
        return hit
    hit = cache.get_normalized(normalized)
    if hit and hit.argv:
        return hit
    if intent:
        hit = cache.get_intent_entity(intent, entity)
        if hit and hit.argv:
            return hit
    if flow_id:
        hit = cache.get_flow(flow_id)
        if hit and hit.argv:
            return hit
    return None

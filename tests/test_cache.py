from core.cache import CachedResolution, MemoryPhraseCache, lookup_layers


def test_layer_order_exact_wins() -> None:
    cache = MemoryPhraseCache()
    exact = CachedResolution(flow_id="1", argv=["echo", "exact"], flow_confidence=1.0)
    normalized = CachedResolution(flow_id="2", argv=["echo", "norm"], flow_confidence=1.0)
    cache.put_exact("Lance Firefox", exact)
    cache.put_normalized("lance firefox", normalized)
    hit = lookup_layers(
        cache, phrase="Lance Firefox", normalized="lance firefox", intent="launch_program"
    )
    assert hit is not None
    assert hit.layer == "L1"
    assert hit.argv == ["echo", "exact"]


def test_l2_then_l3() -> None:
    cache = MemoryPhraseCache()
    cache.put_normalized(
        "lance firefox",
        CachedResolution(flow_id="2", argv=["echo", "norm"], flow_confidence=0.95),
    )
    hit = lookup_layers(cache, phrase="Lance Firefox", normalized="lance firefox")
    assert hit is not None
    assert hit.layer == "L2"

    cache = MemoryPhraseCache()
    cache.put_intent_entity(
        "launch_program",
        "Firefox",
        CachedResolution(flow_id="3", argv=["echo", "ie"], flow_confidence=0.9),
    )
    hit = lookup_layers(
        cache,
        phrase="x",
        normalized="y",
        intent="launch_program",
        entity="Firefox",
    )
    assert hit is not None
    assert hit.layer == "L3"

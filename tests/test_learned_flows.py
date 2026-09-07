from __future__ import annotations

import pytest

from apps.flows.models import Flow
from apps.knowledge.models import IntentAlias
from apps.requests import services
from core.cache import MemoryPhraseCache
from core.engine import Pipeline
from core.execution.local import LocalSubprocessExecutor
from core.llm import (
    ActionProposal,
    EntityProposal,
    HermesProposal,
    IntentProposal,
    LLMResult,
    LLMUsage,
)


class CountingLLM:
    def __init__(self, proposal: HermesProposal) -> None:
        self.proposal = proposal
        self.calls = 0

    def generate_structured(self, payload: dict) -> LLMResult:
        self.calls += 1
        return LLMResult(proposal=self.proposal, usage=LLMUsage(), model="fake")

    def ping(self) -> bool:
        return True


def _pipeline(llm: CountingLLM, cache: MemoryPhraseCache) -> Pipeline:
    return Pipeline(
        knowledge=services.DjangoKnowledge(),
        executor=LocalSubprocessExecutor(),
        llm=llm,
        cache=cache,
        confidence_threshold=0.90,
    )


def _clear(cache: MemoryPhraseCache) -> None:
    cache._exact.clear()
    cache._normalized.clear()
    cache._intent_entity.clear()
    cache._flow.clear()


@pytest.mark.django_db
def test_learn_then_replay_update_pc(monkeypatch) -> None:
    llm = CountingLLM(
        HermesProposal(
            intent=IntentProposal(name="update_system", create=True),
            actions=[ActionProposal(argv=["echo", "topgrade"])],
            triggers=["update"],
        )
    )
    cache = MemoryPhraseCache()

    def fake_build() -> Pipeline:
        return _pipeline(llm, cache)

    monkeypatch.setattr(services, "build_pipeline", fake_build)
    first = services.run_execute("hermes update the pc")
    assert first.status == "success"
    assert first.llm_used is True
    assert first.argv == ["echo", "topgrade"]
    assert IntentAlias.objects.filter(normalized_phrase="update").exists()
    assert Flow.objects.filter(intent__name="update_system", enabled=True).count() == 1

    _clear(cache)
    second = services.run_execute("update the pc")
    assert second.status == "success"
    assert second.llm_used is False
    assert second.argv == ["echo", "topgrade"]
    assert llm.calls == 1


@pytest.mark.django_db
def test_learn_then_replay_find_movie(monkeypatch) -> None:
    llm = CountingLLM(
        HermesProposal(
            intent=IntentProposal(name="add_media", create=True),
            entities=[EntityProposal(name="Dune", type="movie")],
            actions=[
                ActionProposal(
                    type="http",
                    extra={
                        "url": "http://127.0.0.1:7878/api/v3/movie",
                        "method": "POST",
                        "body": {"title": "Dune"},
                    },
                )
            ],
            triggers=["find"],
        )
    )
    cache = MemoryPhraseCache()
    seen: list[dict] = []

    def fake_request(method, url, headers=None, json=None, timeout=None):
        seen.append({"method": method, "url": url, "json": json})
        return type("Resp", (), {"status_code": 201, "text": "ok"})()

    monkeypatch.setattr("core.execution.http.httpx.request", fake_request)

    def fake_build() -> Pipeline:
        return _pipeline(llm, cache)

    monkeypatch.setattr(services, "build_pipeline", fake_build)
    first = services.run_execute("find me Dune")
    assert first.status == "success"
    assert first.llm_used is True
    assert seen[0]["json"]["title"] == "Dune"
    flow = Flow.objects.get(intent__name="add_media", enabled=True)
    body = flow.nodes.filter(node_type="action").first().config["extra"]["body"]
    assert body["title"] == "{query}"
    assert flow.confidence >= 0.90

    _clear(cache)
    second = services.run_execute("find me Inception")
    assert second.status == "success"
    assert second.llm_used is False
    assert seen[1]["json"]["title"] == "Inception"
    assert llm.calls == 1
    assert Flow.objects.filter(intent__name="add_media").count() == 1

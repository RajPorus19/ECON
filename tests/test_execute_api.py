from __future__ import annotations

import pytest

from apps.requests import services
from core.engine import Pipeline
from core.execution.local import LocalSubprocessExecutor
from core.llm import ActionProposal, HermesProposal, IntentProposal, LLMResult, LLMUsage


class EmptyKnowledge:
    def intent_aliases(self) -> list[tuple[str, str, float]]:
        return []

    def entity_names(self) -> list[tuple[str, str, float]]:
        return []

    def find_flow(self, intent_name: str, entity_name: str | None):
        return None


class FakeLLM:
    def generate_structured(self, payload: dict) -> LLMResult:
        return LLMResult(
            proposal=HermesProposal(
                intent=IntentProposal(name="shell_execute"),
                actions=[ActionProposal(argv=["echo", "hello"])],
            ),
            usage=LLMUsage(),
            model="fake",
        )

    def ping(self) -> bool:
        return True


@pytest.mark.django_db
def test_execute_echo_via_api(client, monkeypatch) -> None:
    def fake_build_pipeline() -> Pipeline:
        return Pipeline(
            knowledge=EmptyKnowledge(),
            executor=LocalSubprocessExecutor(),
            llm=FakeLLM(),
        )

    monkeypatch.setattr(services, "build_pipeline", fake_build_pipeline)
    response = client.post(
        "/api/v1/execute?debug=true",
        data={"text": "echo hello"},
        content_type="application/json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["llm_used"] is True
    assert body["argv"] == ["echo", "hello"]
    assert "hello" in (body["debug"]["execution"]["stdout"] or "")


@pytest.mark.django_db
def test_learning_runs_when_broker_unavailable(client, monkeypatch) -> None:
    from apps.knowledge.models import Intent

    intent = Intent.objects.create(name="shell_execute", confidence=1.0, usage_count=0)

    def boom(*_args, **_kwargs):
        raise ConnectionError("broker down")

    monkeypatch.setattr("apps.knowledge.tasks.learn_from_execution.delay", boom)

    def fake_build_pipeline() -> Pipeline:
        return Pipeline(
            knowledge=EmptyKnowledge(),
            executor=LocalSubprocessExecutor(),
            llm=FakeLLM(),
        )

    monkeypatch.setattr(services, "build_pipeline", fake_build_pipeline)
    response = client.post(
        "/api/v1/execute",
        data={"text": "echo hello"},
        content_type="application/json",
    )
    assert response.status_code == 200
    intent.refresh_from_db()
    assert intent.usage_count == 1

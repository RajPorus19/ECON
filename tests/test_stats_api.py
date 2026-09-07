import pytest

from apps.knowledge.models import Intent
from apps.requests.models import RequestLog


@pytest.mark.django_db
def test_stats_and_request_list(client) -> None:
    intent = Intent.objects.create(name="launch_program")
    RequestLog.objects.create(
        text="Lance Firefox",
        normalized_text="lance firefox",
        intent=intent,
        llm_used=False,
        status="success",
        duration_ms=20,
        tokens_saved=1200,
    )
    RequestLog.objects.create(
        text="unknown",
        normalized_text="unknown",
        llm_used=True,
        status="success",
        duration_ms=2000,
        tokens_saved=0,
        prompt_tokens=100,
        completion_tokens=50,
    )
    stats = client.get("/api/v1/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["requests_today"] == 2
    assert body["llm_calls"] == 1
    assert body["llm_avoidance"] == 50.0
    assert body["tokens_saved_are_estimated"] is True

    listed = client.get("/api/v1/requests")
    assert listed.status_code == 200
    assert listed.json()["count"] == 2

    opt = client.get("/api/v1/optimizations")
    assert opt.status_code == 200
    assert opt.json()["intents"][0]["intent"] == "launch_program"

import httpx

from core.execution import ExecuteRequest
from core.execution.http import HttpExecutor, interpolate_command


def test_interpolate_steam_command() -> None:
    argv = interpolate_command(
        ["steam", "steam://rungameid/{app_id}"],
        {"app_id": "123"},
    )
    assert argv == ["steam", "steam://rungameid/123"]


def test_http_executor_uses_mock_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = HttpExecutor(client=client).execute(
        ExecuteRequest(argv=["http"], extra={"url": "https://example.test/play", "method": "POST"})
    )
    assert result.success
    assert result.stdout == "ok"

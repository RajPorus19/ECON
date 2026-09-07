import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "voice"))

from econom_voice import EconVoiceClient, EnergyVAD, VoiceConfig


def test_energy_vad_detects_peak() -> None:
    vad = EnergyVAD(threshold=100)
    silent = bytes(32)
    loud = (2000).to_bytes(2, "little", signed=True) * 16
    assert vad.speech_triggered(silent, 16000) is False
    assert vad.speech_triggered(loud, 16000) is True


def test_client_posts(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeResponse:
        def json(self):
            return {"status": "success"}

        text = ""

    def fake_post(url, json, timeout):  # noqa: A002
        calls.append({"url": url, "json": json})
        return FakeResponse()

    monkeypatch.setattr("econom_voice.httpx.post", fake_post)
    client = EconVoiceClient(VoiceConfig(api_url="http://127.0.0.1:8000"))
    result = client.submit("Lance Firefox")
    assert result["status"] == "success"
    assert calls[0]["json"]["text"] == "Lance Firefox"

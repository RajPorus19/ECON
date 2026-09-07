"""STT provider interface. Voice client uses this; Django does not capture audio."""

from __future__ import annotations

from typing import Protocol


class STTProvider(Protocol):
    def transcribe(self, audio_path: str) -> str: ...

    def ping(self) -> bool: ...


class UnavailableSTT:
    def transcribe(self, audio_path: str) -> str:
        raise RuntimeError("STT backend is not installed")

    def ping(self) -> bool:
        return False


def load_stt() -> STTProvider:
    try:
        from econom_voice.stt import FasterWhisperSTT

        return FasterWhisperSTT()
    except Exception:  # noqa: BLE001 — optional extra
        return UnavailableSTT()

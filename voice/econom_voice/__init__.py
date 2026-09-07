"""Voice client: VAD → STT → POST /api/v1/execute. No microphone in Django."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from econom_voice.stt import FasterWhisperSTT


class VADProvider(Protocol):
    def speech_triggered(self, pcm16: bytes, sample_rate: int) -> bool: ...


class STTProvider(Protocol):
    def transcribe(self, audio_path: str) -> str: ...

    def ping(self) -> bool: ...


class EnergyVAD:
    """Tiny amplitude gate used when Silero is not installed."""

    def __init__(self, threshold: int = 500) -> None:
        self.threshold = threshold

    def speech_triggered(self, pcm16: bytes, sample_rate: int) -> bool:
        if len(pcm16) < 4:
            return False
        peak = max(
            abs(int.from_bytes(pcm16[i : i + 2], "little", signed=True))
            for i in range(0, len(pcm16) - 1, 2)
        )
        return peak >= self.threshold


class SileroVAD:
    """Runs a Silero-style callable on PCM16 chunks. EnergyVAD is the fallback."""

    def __init__(self, model: object, threshold: float = 0.5) -> None:
        self.model = model
        self.threshold = threshold
        self._fallback = EnergyVAD()

    def speech_triggered(self, pcm16: bytes, sample_rate: int) -> bool:
        samples = _pcm16_to_float(pcm16)
        if not samples:
            return False
        try:
            tensor: object = samples
            try:
                import torch

                tensor = torch.tensor(samples)
            except Exception:  # noqa: BLE001 — tests pass a fake model, no GPU
                tensor = samples
            prob = self.model(tensor, sample_rate)
            if hasattr(prob, "item"):
                prob = prob.item()
            return float(prob) >= self.threshold
        except Exception:  # noqa: BLE001
            return self._fallback.speech_triggered(pcm16, sample_rate)


def _pcm16_to_float(pcm16: bytes) -> list[float]:
    if len(pcm16) < 2:
        return []
    return [
        int.from_bytes(pcm16[i : i + 2], "little", signed=True) / 32768.0
        for i in range(0, len(pcm16) - 1, 2)
    ]


def load_silero_vad() -> VADProvider:
    try:
        from silero_vad import load_silero_vad as _load

        return SileroVAD(_load())
    except Exception:  # noqa: BLE001
        return EnergyVAD()


@dataclass
class VoiceConfig:
    api_url: str = "http://127.0.0.1:8000"
    confirm: bool = False


class EconVoiceClient:
    def __init__(self, config: VoiceConfig | None = None) -> None:
        self.config = config or VoiceConfig()

    def submit(self, text: str) -> dict:
        response = httpx.post(
            f"{self.config.api_url.rstrip('/')}/api/v1/execute",
            json={"text": text, "confirm": self.config.confirm},
            timeout=60.0,
        )
        try:
            return response.json()
        except ValueError:
            return {"status": "error", "message": response.text}


__all__ = [
    "EconVoiceClient",
    "EnergyVAD",
    "FasterWhisperSTT",
    "SileroVAD",
    "VoiceConfig",
    "load_silero_vad",
]

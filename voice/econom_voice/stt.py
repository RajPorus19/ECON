"""STT backends for econom-voice."""

from __future__ import annotations


class FasterWhisperSTT:
    def __init__(self, model_size: str = "base") -> None:
        self.model_size = model_size
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_size, device="cpu")
        return self._model

    def ping(self) -> bool:
        try:
            import faster_whisper  # noqa: F401

            return True
        except Exception:  # noqa: BLE001
            return False

    def transcribe(self, audio_path: str) -> str:
        model = self._load()
        segments, _info = model.transcribe(audio_path)
        return " ".join(segment.text.strip() for segment in segments).strip()

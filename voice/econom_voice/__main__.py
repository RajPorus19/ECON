"""Microphone loop. Optional sounddevice; prints transcribed text and POSTs to ECON."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from econom_voice import EconVoiceClient, EnergyVAD, FasterWhisperSTT, VoiceConfig, load_silero_vad


def cmd_run(args: argparse.Namespace) -> int:
    client = EconVoiceClient(VoiceConfig(api_url=args.api_url, confirm=args.confirm))
    if args.text:
        print(client.submit(args.text))
        return 0

    vad = load_silero_vad() if args.vad == "silero" else EnergyVAD()
    stt = FasterWhisperSTT(model_size=args.model)
    if not stt.ping():
        print("faster-whisper is not installed. Use: pip install -e './voice[voice]'")
        print("You can still pipe text with: econom-voice --text 'Lance Firefox'")
        return 1

    try:
        import numpy as np
        import sounddevice as sd
        import soundfile as sf
    except Exception as exc:  # noqa: BLE001
        print(f"Microphone extras missing ({exc}). Use --text for a dry run.")
        return 1

    sample_rate = 16000
    print("Listening. Ctrl+C to stop.")
    buffer = []
    speaking = False
    silence = 0
    try:
        while True:
            chunk = sd.rec(
                int(0.3 * sample_rate), samplerate=sample_rate, channels=1, dtype="int16"
            )
            sd.wait()
            pcm = chunk.tobytes()
            if vad.speech_triggered(pcm, sample_rate):
                speaking = True
                silence = 0
                buffer.append(chunk.copy())
            elif speaking:
                silence += 1
                buffer.append(chunk.copy())
                if silence >= 4 and buffer:
                    audio = np.concatenate(buffer, axis=0)
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                        path = handle.name
                    sf.write(path, audio, sample_rate)
                    text = stt.transcribe(path)
                    Path(path).unlink(missing_ok=True)
                    buffer = []
                    speaking = False
                    if text:
                        print(f"> {text}")
                        print(client.submit(text))
    except KeyboardInterrupt:
        print("Stopped.")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="econom-voice", description="ECON voice client")
    parser.add_argument(
        "--api-url", default=os.environ.get("ECON_API_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument("--text", help="Skip mic and send this utterance")
    parser.add_argument("--model", default="base")
    parser.add_argument("--vad", choices=["energy", "silero"], default="energy")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    raise SystemExit(cmd_run(args))

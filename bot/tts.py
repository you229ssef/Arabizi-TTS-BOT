"""Local TTS adapter using pyttsx3 and temporary WAV files."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path


class LocalTTS:
    def __init__(self, rate: int = 155, volume: float = 1.0) -> None:
        self.rate = rate
        self.volume = volume

    def _synthesize_sync(self, text: str, output: Path) -> None:
        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError("pyttsx3 is not installed") from exc

        engine = pyttsx3.init()
        engine.setProperty("rate", self.rate)
        engine.setProperty("volume", self.volume)
        engine.save_to_file(text, str(output))
        engine.runAndWait()
        if not output.exists() or output.stat().st_size == 0:
            raise RuntimeError(
                "pyttsx3 did not create audio; install a host speech backend such as espeak-ng"
            )

    async def synthesize(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile(prefix="arabizi-tts-", suffix=".wav", delete=False)
        output = Path(handle.name)
        handle.close()
        try:
            await asyncio.to_thread(self._synthesize_sync, text, output)
        except Exception:
            output.unlink(missing_ok=True)
            raise
        return output


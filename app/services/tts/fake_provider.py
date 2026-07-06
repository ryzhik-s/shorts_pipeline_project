"""Fake TTS — создаёт пустой/silence-файл вместо реального обращения к Edge TTS."""
from pathlib import Path

from app.services.tts.base import TTSProvider


class FakeTTSProvider(TTSProvider):
    async def synthesize(self, *, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Пишем минимальный валидный mp3-заглушку (просто байты-маркер для тестов).
        output_path.write_bytes(b"FAKE_MP3_AUDIO_" + text[:50].encode("utf-8", "ignore"))
        return output_path

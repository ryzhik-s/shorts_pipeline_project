"""Фабрика TTSProvider по настройке TTS_PROVIDER."""
from functools import lru_cache

from app.core.config import get_settings
from app.services.tts.base import TTSProvider


@lru_cache
def get_tts_provider() -> TTSProvider:
    settings = get_settings()

    match settings.tts_provider:
        case "edge":
            from app.services.tts.edge_provider import EdgeTTSProvider

            return EdgeTTSProvider()
        case "fake":
            from app.services.tts.fake_provider import FakeTTSProvider

            return FakeTTSProvider()
        case _:
            raise ValueError(f"Неизвестный TTS_PROVIDER: {settings.tts_provider}")

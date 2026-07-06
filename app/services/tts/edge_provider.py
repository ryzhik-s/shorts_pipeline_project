"""
Реализация TTSProvider через Edge TTS (бесплатные голоса Microsoft Azure Neural).

Библиотека `edge-tts` обращается к публичному edge-сервису Microsoft, который
используется их браузером Edge для функции "Read aloud" — бесплатно, без ключа,
но не имеет официального SLA, поэтому в проде стоит иметь fallback.
"""
import edge_tts

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.tts.base import TTSProvider

logger = get_logger(__name__)


class EdgeTTSProvider(TTSProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self._voice = settings.edge_tts_voice
        self._rate = settings.edge_tts_rate
        self._volume = settings.edge_tts_volume

    async def synthesize(self, *, text: str, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)

        communicate = edge_tts.Communicate(
            text=text,
            voice=self._voice,
            rate=self._rate,
            volume=self._volume,
        )
        await communicate.save(str(output_path))

        logger.info(
            "tts_synthesized",
            voice=self._voice,
            chars=len(text),
            output_path=str(output_path),
        )
        return output_path

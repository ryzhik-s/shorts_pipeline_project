"""
Шаг 1: извлечение субтитров из исходного видео.

Используем faster-whisper (CTranslate2-реализация Whisper — быстрее и легче
оригинального openai-whisper на CPU, что важно для портфолио-проекта без GPU).

Результат — список сегментов {start, end, text}, которые дальше анализирует LLM.
"""
from pathlib import Path

from faster_whisper import WhisperModel

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_model_cache: WhisperModel | None = None


def _get_whisper_model() -> WhisperModel:
    global _model_cache
    if _model_cache is None:
        settings = get_settings()
        _model_cache = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type="int8" if settings.whisper_device == "cpu" else "float16",
        )
    return _model_cache


def extract_subtitles(video_path: Path) -> dict:
    """
    Извлекает речь из видео и возвращает субтитры в формате:
    {"segments": [{"start": 0.0, "end": 3.2, "text": "..."}], "language": "ru"}
    """
    model = _get_whisper_model()
    segments_iter, info = model.transcribe(str(video_path), beam_size=5)

    segments = [
        {"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()}
        for seg in segments_iter
    ]

    logger.info(
        "subtitles_extracted",
        video_path=str(video_path),
        segments_count=len(segments),
        language=info.language,
    )

    return {"segments": segments, "language": info.language}

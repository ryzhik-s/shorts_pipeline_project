"""
Шаг 4: GPT/Claude определяет, какие именно отрезки исходного видео
(по таймкодам субтитров) нужно вырезать, чтобы визуально проиллюстрировать
ключевые моменты сценария.

Это отдельный шаг от write_script, т.к. сценарий — это текст для НОВОЙ озвучки,
а таймкоды — это выбор кадров из ОРИГИНАЛЬНОГО видео, которые будут визуальным
рядом (с приглушённым/убранным оригинальным звуком, см. cut_video step).
"""
import time

from app.core.logging import get_logger
from app.monitoring.metrics import LLM_REQUEST_DURATION, LLM_REQUEST_FAILURES
from app.services.llm.base import LLMProvider

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
На основе субтитров оригинального видео и сценария Shorts-ролика выбери
конкретные тайм-коды (start/end в секундах ОТНОСИТЕЛЬНО ОРИГИНАЛЬНОГО видео),
которые визуально иллюстрируют сценарий. Выбирай только сегменты, где
происходит что-то визуально значимое (действие, эмоция, ключевая сцена).

Суммарная длительность выбранных сегментов не должна сильно превышать
целевую длительность ролика (с запасом +20% на монтаж).

Отвечай в формате JSON:
{
  "timecodes": [
    {"start": 12.5, "end": 18.0, "reason": "почему этот момент важен"},
    {"start": 45.0, "end": 52.0, "reason": "..."}
  ]
}
"""


async def generate_timecodes(
    llm: LLMProvider,
    *,
    original_subtitles: dict,
    script: dict,
    target_duration: int,
    provider_name: str,
) -> dict:
    transcript_text = "\n".join(
        f"[{seg['start']}-{seg['end']}] {seg['text']}"
        for seg in original_subtitles["segments"]
    )
    user_prompt = (
        f"Целевая длительность ролика: {target_duration} секунд\n\n"
        f"Сценарий (для контекста, НЕ для тайм-кодов): {script.get('voiceover_text')}\n\n"
        f"Субтитры оригинального видео с тайм-кодами:\n{transcript_text}"
    )

    start = time.monotonic()
    try:
        result = await llm.complete_json(
            system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt, max_tokens=1024
        )
    except Exception:
        LLM_REQUEST_FAILURES.labels(provider=provider_name).inc()
        raise
    finally:
        LLM_REQUEST_DURATION.labels(provider=provider_name).observe(time.monotonic() - start)

    logger.info("timecodes_generated", count=len(result.get("timecodes", [])))
    return result

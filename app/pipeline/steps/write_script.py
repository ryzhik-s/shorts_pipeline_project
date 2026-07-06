"""Шаг 3: GPT/Claude пишет сценарий озвучки и субтитров для Shorts-ролика."""
import time

from app.core.logging import get_logger
from app.monitoring.metrics import LLM_REQUEST_DURATION, LLM_REQUEST_FAILURES
from app.services.llm.base import LLMProvider

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
Ты пишешь сценарий для короткого вертикального видео (YouTube Shorts) длиной
{target_duration} секунд на основе анализа сюжета эпизода.

Структура ролика:
  1. Завязка/хук — заинтересовать зрителя в первые 3 секунды
  2. Развитие — 1-2 ключевых момента истории
  3. Вывод/мораль — чёткая мысль в конце

Сценарий должен быть написан как ТЕКСТ ОЗВУЧКИ (voiceover) от первого лица
рассказчика, динамичный, без лишних слов — каждое предложение должно нести
смысл. Также разбей текст на сегменты субтитров (по 3-8 слов на сегмент,
с тайм-кодами относительно начала озвучки, начиная с 0.0).

Отвечай в формате JSON:
{{
  "title": "короткий заголовок ролика",
  "voiceover_text": "полный текст для озвучки",
  "subtitles": [
    {{"start": 0.0, "end": 2.5, "text": "первый сегмент субтитров"}},
    {{"start": 2.5, "end": 5.0, "text": "второй сегмент"}}
  ]
}}
"""


async def write_script(
    llm: LLMProvider, *, plot_analysis: dict, target_duration: int, provider_name: str
) -> dict:
    system_prompt = _SYSTEM_PROMPT.format(target_duration=target_duration)
    user_prompt = (
        f"Анализ сюжета:\n"
        f"Краткое описание: {plot_analysis.get('summary')}\n"
        f"Ключевые моменты: {plot_analysis.get('key_moments')}\n"
        f"Мораль: {plot_analysis.get('moral')}"
    )

    start = time.monotonic()
    try:
        result = await llm.complete_json(
            system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=1536
        )
    except Exception:
        LLM_REQUEST_FAILURES.labels(provider=provider_name).inc()
        raise
    finally:
        LLM_REQUEST_DURATION.labels(provider=provider_name).observe(time.monotonic() - start)

    logger.info("script_written", title=result.get("title"))
    return result

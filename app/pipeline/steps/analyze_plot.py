"""Шаг 2: GPT/Claude анализирует сюжет эпизода по извлечённым субтитрам."""
import time

from app.core.logging import get_logger
from app.monitoring.metrics import LLM_REQUEST_DURATION, LLM_REQUEST_FAILURES
from app.services.llm.base import LLMProvider

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
Ты — опытный сценарист, который анализирует сюжет эпизода мультсериала
для создания короткого вертикального видео (Shorts) длиной 40-60 секунд.

Твоя задача — выделить ОДНУ ключевую мысль/мораль эпизода и 2-4 ключевых
момента сюжета, которые её иллюстрируют. Не пересказывай весь эпизод —
фокусируйся только на той части истории, которая нужна для короткого ролика
с чёткой мыслью в начале и выводом в конце.

Отвечай в формате JSON:
{
  "summary": "краткое описание сюжетной арки в 1-2 предложения",
  "key_moments": ["момент 1", "момент 2", "момент 3"],
  "moral": "главный вывод/мораль эпизода в одном предложении"
}
"""


async def analyze_plot(llm: LLMProvider, *, subtitles: dict, provider_name: str) -> dict:
    transcript_text = "\n".join(
        f"[{seg['start']}-{seg['end']}] {seg['text']}" for seg in subtitles["segments"]
    )
    user_prompt = f"Субтитры эпизода:\n\n{transcript_text}"

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

    logger.info("plot_analyzed", moral=result.get("moral"))
    return result

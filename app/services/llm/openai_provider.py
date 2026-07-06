"""Реализация LLMProvider через OpenAI Chat Completions API."""
import json

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.base import LLMProvider

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY не задан, а LLM_PROVIDER=openai")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def complete_json(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int = 2048
    ) -> dict:
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        logger.debug("openai_response_received", model=self._model, chars=len(content or ""))
        return json.loads(content or "{}")

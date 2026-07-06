"""Реализация LLMProvider через Anthropic Messages API."""
import json
import re

from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.base import LLMProvider

logger = get_logger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY не задан, а LLM_PROVIDER=anthropic")
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def complete_json(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int = 2048
    ) -> dict:
        # Claude не имеет отдельного "json_object" режима как OpenAI,
        # поэтому явно просим JSON в system prompt и парсим текстовый ответ.
        full_system = (
            f"{system_prompt}\n\n"
            "Отвечай ТОЛЬКО валидным JSON-объектом, без markdown-разметки, "
            "без пояснений до или после."
        )
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=full_system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        logger.debug("anthropic_response_received", model=self._model, chars=len(text))

        match = _JSON_BLOCK_RE.search(text)
        if not match:
            raise ValueError(f"Anthropic не вернул JSON-объект: {text[:200]!r}")
        return json.loads(match.group(0))

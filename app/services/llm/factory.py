"""Фабрика: выбирает конкретную реализацию LLMProvider по настройке LLM_PROVIDER."""
from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.base import LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()

    match settings.llm_provider:
        case "openai":
            from app.services.llm.openai_provider import OpenAIProvider

            return OpenAIProvider()
        case "anthropic":
            from app.services.llm.anthropic_provider import AnthropicProvider

            return AnthropicProvider()
        case "fake":
            from app.services.llm.fake_provider import FakeLLMProvider

            return FakeLLMProvider()
        case _:
            raise ValueError(f"Неизвестный LLM_PROVIDER: {settings.llm_provider}")

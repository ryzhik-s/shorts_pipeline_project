"""
Абстрактный интерфейс LLM-провайдера (паттерн Strategy/Adapter).

Pipeline-степы (analyze_plot, write_script, generate_timecodes) зависят
только от этого интерфейса, а не от конкретного OpenAI/Anthropic SDK.
Это позволяет:
  - менять провайдера через одну переменную окружения (LLM_PROVIDER)
  - подменять провайдер на FakeLLMProvider в тестах без сетевых вызовов
  - добавлять новых провайдеров (Gemini, локальные модели) без изменения pipeline
"""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Контракт: 'дай структурированный JSON-ответ на промпт'."""

    @abstractmethod
    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
    ) -> dict:
        """
        Отправляет промпт модели и возвращает распарсенный JSON-объект.

        Конкретные реализации сами отвечают за:
          - указание модели генерировать только JSON (response_format / промпт-инструкция)
          - retry при сетевых сбоях
          - парсинг и валидацию того, что ответ — валидный JSON
        """
        raise NotImplementedError

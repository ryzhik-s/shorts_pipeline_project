"""Тесты FakeLLMProvider — проверяем, что детерминированные ответы доступны для всех шагов."""
import pytest

from app.services.llm.fake_provider import FakeLLMProvider


@pytest.mark.asyncio
async def test_fake_provider_returns_plot_analysis_by_default():
    provider = FakeLLMProvider()
    result = await provider.complete_json(
        system_prompt="Ты анализируешь сюжет", user_prompt="субтитры эпизода"
    )

    assert "summary" in result
    assert "key_moments" in result
    assert "moral" in result
    assert isinstance(result["key_moments"], list)


@pytest.mark.asyncio
async def test_fake_provider_returns_script_when_prompt_mentions_script():
    provider = FakeLLMProvider()
    result = await provider.complete_json(
        system_prompt="Ты пишешь сценарий для Shorts", user_prompt="анализ сюжета..."
    )

    assert "voiceover_text" in result
    assert "subtitles" in result
    assert len(result["subtitles"]) > 0
    assert all({"start", "end", "text"} <= seg.keys() for seg in result["subtitles"])


@pytest.mark.asyncio
async def test_fake_provider_returns_timecodes_when_prompt_mentions_timecodes():
    provider = FakeLLMProvider()
    result = await provider.complete_json(
        system_prompt="Выбери тайм-коды для нарезки", user_prompt="субтитры..."
    )

    assert "timecodes" in result
    for tc in result["timecodes"]:
        assert tc["end"] > tc["start"]

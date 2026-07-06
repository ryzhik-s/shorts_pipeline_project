"""Тесты LLM-зависимых шагов пайплайна, используют FakeLLMProvider."""
import pytest

from app.pipeline.steps.analyze_plot import analyze_plot
from app.pipeline.steps.generate_timecodes import generate_timecodes
from app.pipeline.steps.write_script import write_script
from app.services.llm.fake_provider import FakeLLMProvider


@pytest.mark.asyncio
async def test_analyze_plot_returns_moral_and_key_moments(fake_subtitles):
    llm = FakeLLMProvider()
    result = await analyze_plot(llm, subtitles=fake_subtitles, provider_name="fake")

    assert result["moral"]
    assert len(result["key_moments"]) >= 1


@pytest.mark.asyncio
async def test_write_script_produces_voiceover_and_subtitles():
    llm = FakeLLMProvider()
    plot_analysis = {
        "summary": "Тестовый сюжет",
        "key_moments": ["момент 1", "момент 2"],
        "moral": "Тестовая мораль",
    }

    result = await write_script(
        llm, plot_analysis=plot_analysis, target_duration=55, provider_name="fake"
    )

    assert result["voiceover_text"]
    assert isinstance(result["subtitles"], list)
    assert all(seg["end"] > seg["start"] for seg in result["subtitles"])


@pytest.mark.asyncio
async def test_generate_timecodes_returns_non_overlapping_segments(fake_subtitles):
    llm = FakeLLMProvider()
    script = {"voiceover_text": "какой-то текст сценария"}

    result = await generate_timecodes(
        llm,
        original_subtitles=fake_subtitles,
        script=script,
        target_duration=55,
        provider_name="fake",
    )

    timecodes = result["timecodes"]
    assert len(timecodes) > 0
    for tc in timecodes:
        assert tc["start"] < tc["end"]

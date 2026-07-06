"""
Тесты ffmpeg_utils — мокируем asyncio.create_subprocess_exec, чтобы не зависеть
от реального бинаря ffmpeg в unit-тестах (это покрывается отдельным integration-тестом
с маркером @pytest.mark.ffmpeg, который запускается только если ffmpeg доступен).
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.steps import ffmpeg_utils
from app.pipeline.steps.ffmpeg_utils import FFmpegError


def _mock_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""):
    process = MagicMock()
    process.returncode = returncode
    process.communicate = AsyncMock(return_value=(stdout, stderr))
    return process


@pytest.mark.asyncio
async def test_cut_segments_builds_filter_complex_and_calls_ffmpeg(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake video bytes")
    output = tmp_path / "output.mp4"

    with patch(
        "asyncio.create_subprocess_exec", new=AsyncMock(return_value=_mock_process())
    ) as mock_exec:
        result = await ffmpeg_utils.cut_segments(
            source_path=source,
            segments=[{"start": 1.0, "end": 5.0}, {"start": 10.0, "end": 15.0}],
            output_path=output,
            target_width=1080,
            target_height=1920,
        )

    assert result == output
    mock_exec.assert_called_once()
    called_args = mock_exec.call_args[0]
    assert "ffmpeg" in called_args[0]
    assert "-filter_complex" in called_args


@pytest.mark.asyncio
async def test_cut_segments_raises_on_empty_segments(tmp_path: Path):
    with pytest.raises(ValueError, match="пуст"):
        await ffmpeg_utils.cut_segments(
            source_path=tmp_path / "source.mp4",
            segments=[],
            output_path=tmp_path / "output.mp4",
            target_width=1080,
            target_height=1920,
        )


@pytest.mark.asyncio
async def test_run_subprocess_raises_ffmpeg_error_on_failure():
    with patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=_mock_process(returncode=1, stderr=b"invalid input")),
    ):
        with pytest.raises(FFmpegError, match="invalid input"):
            await ffmpeg_utils._run_subprocess(["ffmpeg", "-bad-arg"])


@pytest.mark.asyncio
async def test_mux_voiceover_calls_ffmpeg_with_correct_mapping(tmp_path: Path):
    video = tmp_path / "video.mp4"
    voiceover = tmp_path / "voice.mp3"
    output = tmp_path / "out.mp4"

    with patch(
        "asyncio.create_subprocess_exec", new=AsyncMock(return_value=_mock_process())
    ) as mock_exec:
        await ffmpeg_utils.mux_voiceover(
            video_path=video, voiceover_path=voiceover, output_path=output
        )

    called_args = mock_exec.call_args[0]
    assert "-map" in called_args
    assert "0:v:0" in called_args
    assert "1:a:0" in called_args


@pytest.mark.asyncio
async def test_burn_subtitles_includes_subtitles_filter(tmp_path: Path):
    video = tmp_path / "video.mp4"
    srt = tmp_path / "subs.srt"
    output = tmp_path / "out.mp4"

    with patch(
        "asyncio.create_subprocess_exec", new=AsyncMock(return_value=_mock_process())
    ) as mock_exec:
        await ffmpeg_utils.burn_subtitles(video_path=video, srt_path=srt, output_path=output)

    called_args = mock_exec.call_args[0]
    vf_index = called_args.index("-vf")
    assert "subtitles=" in called_args[vf_index + 1]

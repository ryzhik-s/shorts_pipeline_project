"""Тесты генерации .srt файла из сегментов субтитров."""
from pathlib import Path

from app.pipeline.steps.srt_utils import _format_srt_timestamp, write_srt_file


def test_format_srt_timestamp_basic():
    assert _format_srt_timestamp(0.0) == "00:00:00,000"
    assert _format_srt_timestamp(65.5) == "00:01:05,500"
    assert _format_srt_timestamp(3661.25) == "01:01:01,250"


def test_write_srt_file_creates_valid_format(tmp_path: Path):
    segments = [
        {"start": 0.0, "end": 2.5, "text": "Привет, это первый сегмент."},
        {"start": 2.5, "end": 5.0, "text": "А это второй сегмент."},
    ]
    output_path = tmp_path / "subs.srt"

    result = write_srt_file(segments, output_path)

    assert result == output_path
    content = output_path.read_text(encoding="utf-8")

    assert "1\n00:00:00,000 --> 00:00:02,500" in content
    assert "Привет, это первый сегмент." in content
    assert "2\n00:00:02,500 --> 00:00:05,000" in content
    assert "А это второй сегмент." in content

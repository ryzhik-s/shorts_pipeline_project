"""Генерация .srt файла субтитров из списка сегментов {start, end, text}."""
from pathlib import Path


def _format_srt_timestamp(seconds: float) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int(round((secs - int(secs)) * 1000))
    return f"{int(hours):02d}:{int(minutes):02d}:{int(secs):02d},{millis:03d}"


def write_srt_file(segments: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for index, seg in enumerate(segments, start=1):
        start_ts = _format_srt_timestamp(seg["start"])
        end_ts = _format_srt_timestamp(seg["end"])
        lines.append(str(index))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(seg["text"])
        lines.append("")  # пустая строка-разделитель между блоками

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

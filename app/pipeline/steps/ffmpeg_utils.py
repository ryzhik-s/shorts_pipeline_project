"""
Низкоуровневые обёртки над FFmpeg/FFprobe.

Запускаем ffmpeg как subprocess (через asyncio.create_subprocess_exec),
чтобы не блокировать event loop FastAPI/Celery worker во время резки видео.
"""
import asyncio
import json
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FFmpegError(RuntimeError):
    """Поднимается, когда ffmpeg/ffprobe завершился с ненулевым кодом возврата."""


async def _run_subprocess(command: list[str]) -> tuple[str, str]:
    log = logger.bind(command=" ".join(command))
    log.debug("ffmpeg_command_started")

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        log.error("ffmpeg_command_failed", returncode=process.returncode, stderr=stderr.decode())
        raise FFmpegError(
            f"Команда завершилась с кодом {process.returncode}: {stderr.decode()[:500]}"
        )

    return stdout.decode(), stderr.decode()


async def probe_duration(video_path: Path) -> float:
    """Возвращает длительность видео в секундах через ffprobe."""
    settings = get_settings()
    stdout, _ = await _run_subprocess(
        [
            settings.ffprobe_binary,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(video_path),
        ]
    )
    data = json.loads(stdout)
    return float(data["format"]["duration"])


async def cut_segments(
    *,
    source_path: Path,
    segments: list[dict],
    output_path: Path,
    target_width: int,
    target_height: int,
) -> Path:
    """
    Вырезает несколько сегментов из source_path по таймкодам [{"start","end"}, ...],
    конкатенирует их в один файл и приводит к вертикальному формату (crop+scale).

    Реализация через filter_complex: trim+setpts на каждый сегмент, затем concat.
    Это избегает проблем с keyframe-выравниванием, которые бывают при -ss/-t
    на уровне контейнера без точной нарезки по кадрам.
    """
    settings = get_settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not segments:
        raise ValueError("Список сегментов для нарезки пуст")

    filter_parts = []
    concat_inputs = []
    for i, seg in enumerate(segments):
        # Обрезаем по времени и сразу приводим к целевому вертикальному кадру:
        # scale по высоте + crop по ширине (или наоборот) для заполнения 9:16 без полос.
        filter_parts.append(
            f"[0:v]trim=start={seg['start']}:end={seg['end']},"
            f"setpts=PTS-STARTPTS,"
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height}[v{i}];"
            f"[0:a]atrim=start={seg['start']}:end={seg['end']},"
            f"asetpts=PTS-STARTPTS[a{i}]"
        )
        concat_inputs.append(f"[v{i}][a{i}]")

    concat_filter = (
        "".join(filter_parts)
        + ";"
        + "".join(concat_inputs)
        + f"concat=n={len(segments)}:v=1:a=1[outv][outa]"
    )

    command = [
        settings.ffmpeg_binary,
        "-y",
        "-i",
        str(source_path),
        "-filter_complex",
        concat_filter,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        str(output_path),
    ]
    await _run_subprocess(command)

    logger.info("video_cut_completed", segments_count=len(segments), output_path=str(output_path))
    return output_path


async def mux_voiceover(
    *, video_path: Path, voiceover_path: Path, output_path: Path
) -> Path:
    """Заменяет аудиодорожку видео на сгенерированную озвучку."""
    settings = get_settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        settings.ffmpeg_binary,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(voiceover_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    await _run_subprocess(command)
    logger.info("voiceover_muxed", output_path=str(output_path))
    return output_path


async def burn_subtitles(
    *, video_path: Path, srt_path: Path, output_path: Path
) -> Path:
    """Вшивает (burn-in) субтитры из .srt файла прямо в видео-дорожку."""
    settings = get_settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Стилизация субтитров: крупный читаемый шрифт, белый текст с чёрной обводкой —
    # стандарт для Shorts/TikTok-формата, чтобы текст не сливался с фоном.
    style = (
        "FontName=Arial,FontSize=14,PrimaryColour=&HFFFFFF,"
        "OutlineColour=&H000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=80"
    )
    command = [
        settings.ffmpeg_binary,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"subtitles={srt_path}:force_style='{style}'",
        "-c:a",
        "copy",
        str(output_path),
    ]
    await _run_subprocess(command)
    logger.info("subtitles_burned", output_path=str(output_path))
    return output_path

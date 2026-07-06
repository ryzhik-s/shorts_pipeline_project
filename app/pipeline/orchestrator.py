"""
Оркестратор пайплайна — связывает все шаги в единую последовательность:

  extract_subtitles -> analyze_plot -> write_script -> generate_timecodes
    -> cut_video -> generate_voiceover -> burn_subtitles

Каждый шаг оборачивается track_pipeline_step (метрики + БД + логи) и
оборачивается в try/except на уровне run_pipeline для корректной финализации
статуса job при любой ошибке (см. JOBS_TOTAL{status="failed"}).

Эта функция вызывается из Celery-задачи (app.workers.tasks), а не напрямую
из HTTP-обработчика — обработка видео занимает минуты, поэтому всегда async job.
"""
import time
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Job, JobStatus, PipelineStep
from app.monitoring.metrics import JOB_PROCESSING_DURATION, JOBS_IN_PROGRESS, JOBS_TOTAL
from app.monitoring.step_tracker import track_pipeline_step
from app.pipeline.steps import ffmpeg_utils
from app.pipeline.steps.analyze_plot import analyze_plot
from app.pipeline.steps.extract_subtitles import extract_subtitles
from app.pipeline.steps.generate_timecodes import generate_timecodes
from app.pipeline.steps.srt_utils import write_srt_file
from app.pipeline.steps.write_script import write_script
from app.services.llm.base import LLMProvider
from app.services.storage.base import StorageBackend
from app.services.tts.base import TTSProvider

logger = get_logger(__name__)


async def run_pipeline(
    *,
    db: AsyncSession,
    job: Job,
    llm: LLMProvider,
    tts: TTSProvider,
    storage: StorageBackend,
    llm_provider_name: str,
) -> None:
    settings = get_settings()
    log = logger.bind(job_id=str(job.id))

    job.status = JobStatus.RUNNING
    await db.commit()
    JOBS_IN_PROGRESS.inc()

    pipeline_start = time.monotonic()
    workspace = storage.job_workspace(str(job.id))
    source_path = storage.resolve_path(job.source_video_path)

    try:
        # 1. Извлечение субтитров из исходного видео
        async with track_pipeline_step(db=db, job=job, step=PipelineStep.EXTRACT_SUBTITLES):
            subtitles = extract_subtitles(source_path)
            job.subtitles = subtitles
            await db.commit()

        # 2. LLM анализирует сюжет
        async with track_pipeline_step(db=db, job=job, step=PipelineStep.ANALYZE_PLOT):
            plot_analysis = await analyze_plot(
                llm, subtitles=subtitles, provider_name=llm_provider_name
            )
            job.plot_analysis = plot_analysis
            await db.commit()

        # 3. LLM пишет сценарий озвучки + субтитров для Shorts
        async with track_pipeline_step(db=db, job=job, step=PipelineStep.WRITE_SCRIPT):
            script = await write_script(
                llm,
                plot_analysis=plot_analysis,
                target_duration=job.target_duration_seconds,
                provider_name=llm_provider_name,
            )
            job.script = script
            await db.commit()

        # 4. LLM выбирает тайм-коды для визуальной нарезки оригинала
        async with track_pipeline_step(db=db, job=job, step=PipelineStep.GENERATE_TIMECODES):
            timecodes_result = await generate_timecodes(
                llm,
                original_subtitles=subtitles,
                script=script,
                target_duration=job.target_duration_seconds,
                provider_name=llm_provider_name,
            )
            job.timecodes = timecodes_result
            await db.commit()

        # 5. FFmpeg режет видео по тайм-кодам и приводит к вертикальному формату
        async with track_pipeline_step(db=db, job=job, step=PipelineStep.CUT_VIDEO):
            cut_path = workspace / "cut.mp4"
            await ffmpeg_utils.cut_segments(
                source_path=source_path,
                segments=timecodes_result["timecodes"],
                output_path=cut_path,
                target_width=settings.target_video_width,
                target_height=settings.target_video_height,
            )
            job.cut_video_path = str(cut_path)
            await db.commit()

        # 6. Генерация озвучки (Edge TTS) по тексту сценария
        async with track_pipeline_step(db=db, job=job, step=PipelineStep.GENERATE_VOICEOVER):
            voiceover_path = workspace / "voiceover.mp3"
            await tts.synthesize(text=script["voiceover_text"], output_path=voiceover_path)
            job.voiceover_path = str(voiceover_path)
            await db.commit()

            muxed_path = workspace / "with_voiceover.mp4"
            await ffmpeg_utils.mux_voiceover(
                video_path=cut_path, voiceover_path=voiceover_path, output_path=muxed_path
            )

        # 7. Вшивание субтитров в финальное видео
        async with track_pipeline_step(db=db, job=job, step=PipelineStep.BURN_SUBTITLES):
            srt_path = workspace / "subtitles.srt"
            write_srt_file(script["subtitles"], srt_path)

            final_path = workspace / "final_short.mp4"
            await ffmpeg_utils.burn_subtitles(
                video_path=muxed_path, srt_path=srt_path, output_path=final_path
            )
            job.output_video_path = str(final_path)

        job.status = JobStatus.SUCCESS
        job.current_step = None
        await db.commit()

        JOBS_TOTAL.labels(status="success").inc()
        log.info("pipeline_completed", output_path=job.output_video_path)

    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        await db.commit()

        JOBS_TOTAL.labels(status="failed").inc()
        log.error("pipeline_failed", error=str(exc), exc_info=True)
        raise

    finally:
        JOBS_IN_PROGRESS.dec()
        JOB_PROCESSING_DURATION.observe(time.monotonic() - pipeline_start)

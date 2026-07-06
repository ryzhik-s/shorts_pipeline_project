"""
Контекст-менеджер для выполнения одного шага pipeline с автоматическим:
  - замером длительности и записью в Prometheus Histogram
  - логированием начала/конца/ошибки (structured logging)
  - записью PipelineStepRun в БД (для истории/отображения прогресса)
  - отправкой исключения в Sentry (через стандартный механизм sentry_sdk)

Это единая точка инструментации — каждый pipeline-степ оборачивается этим
менеджером, и метрики/логи/БД автоматически синхронизированы между собой.
"""
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Job, JobStatus, PipelineStep, PipelineStepRun
from app.monitoring.metrics import PIPELINE_STEP_DURATION, PIPELINE_STEP_FAILURES

logger = get_logger(__name__)


@asynccontextmanager
async def track_pipeline_step(
    *, db: AsyncSession, job: Job, step: PipelineStep
) -> AsyncIterator[None]:
    job.current_step = step
    step_run = PipelineStepRun(job_id=job.id, step=step, status=JobStatus.RUNNING)
    db.add(step_run)
    await db.commit()

    log = logger.bind(job_id=str(job.id), step=step.value)
    log.info("pipeline_step_started")
    start = time.monotonic()

    try:
        yield
    except Exception as exc:
        duration = time.monotonic() - start
        PIPELINE_STEP_DURATION.labels(step=step.value).observe(duration)
        PIPELINE_STEP_FAILURES.labels(step=step.value).inc()

        step_run.status = JobStatus.FAILED
        step_run.duration_seconds = duration
        step_run.error_message = str(exc)
        from sqlalchemy import func

        step_run.finished_at = func.now()
        await db.commit()

        log.error("pipeline_step_failed", duration_seconds=duration, error=str(exc))
        raise
    else:
        duration = time.monotonic() - start
        PIPELINE_STEP_DURATION.labels(step=step.value).observe(duration)

        step_run.status = JobStatus.SUCCESS
        step_run.duration_seconds = duration
        from sqlalchemy import func

        step_run.finished_at = func.now()
        await db.commit()

        log.info("pipeline_step_completed", duration_seconds=duration)

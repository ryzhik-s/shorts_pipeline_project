"""
Celery-задачи.

process_video_job — единственная задача, запускающая полный pipeline для job.
Celery worker сам по себе синхронный, поэтому внутри задачи мы запускаем
asyncio event loop через asyncio.run для работы с async SQLAlchemy/LLM/TTS клиентами.
"""
import asyncio
import uuid

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.sentry import configure_sentry
from app.db.models import Job
from app.db.session import AsyncSessionLocal
from app.pipeline.orchestrator import run_pipeline
from app.services.llm.factory import get_llm_provider
from app.services.storage.factory import get_storage_backend
from app.services.tts.factory import get_tts_provider
from app.workers.celery_app import celery_app

configure_logging()
configure_sentry()
logger = get_logger(__name__)


async def _process_video_job_async(job_id: str) -> None:
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        if job is None:
            logger.error("job_not_found", job_id=job_id)
            return

        settings = get_settings()
        llm = get_llm_provider()
        tts = get_tts_provider()
        storage = get_storage_backend()

        await run_pipeline(
            db=db,
            job=job,
            llm=llm,
            tts=tts,
            storage=storage,
            llm_provider_name=settings.llm_provider,
        )


@celery_app.task(
    name="process_video_job",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def process_video_job(self, job_id: str) -> str:
    """
    Точка входа для Celery worker. Синхронная обёртка над асинхронным pipeline.

    Ретраи: при сетевых сбоях LLM/TTS providers уже есть retry внутри (tenacity),
    но на случай полного сбоя БД/инфраструктуры даём Celery 2 дополнительные попытки.
    """
    log = logger.bind(job_id=job_id, celery_task_id=self.request.id)
    log.info("celery_task_started")

    try:
        asyncio.run(_process_video_job_async(job_id))
    except Exception as exc:
        log.error("celery_task_failed", error=str(exc))
        raise self.retry(exc=exc) from exc

    log.info("celery_task_completed")
    return job_id

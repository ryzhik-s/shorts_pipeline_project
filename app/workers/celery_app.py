"""
Celery-приложение.

Брокер и result backend — Redis (см. core.config). Очередь задач инспектируется
через Flower (см. docker-compose: сервис flower на порту 5555).
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "shorts_pipeline",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_time_limit=settings.celery_task_time_limit_seconds,
    task_track_started=True,
    # Worker подтверждает задачу только после её завершения — если worker
    # упадёт во время обработки, задача вернётся в очередь, а не потеряется.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_extended=True,
)

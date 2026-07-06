"""
Точка входа FastAPI-приложения.

Подключает:
  - роуты API (jobs, health)
  - Prometheus instrumentator (/metrics эндпоинт со стандартными HTTP-метриками)
  - Sentry (если задан SENTRY_DSN)
  - структурированное логирование
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import health, jobs
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.sentry import configure_sentry

settings = get_settings()
configure_logging()
configure_sentry()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", environment=settings.environment)
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title="AI Shorts Pipeline",
    description=(
        "Автоматизированный пайплайн превращения длинных видео в YouTube Shorts: "
        "извлечение субтитров -> анализ сюжета (LLM) -> сценарий -> тайм-коды -> "
        "нарезка FFmpeg -> озвучка -> субтитры."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(jobs.router, prefix=settings.api_v1_prefix)

# /metrics эндпоинт для Prometheus scraping. exclude /health и /metrics из самих метрик,
# чтобы health-check запросы не засоряли латентность HTTP-метрик.
Instrumentator(
    excluded_handlers=["/health", "/metrics"],
    should_group_status_codes=True,
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

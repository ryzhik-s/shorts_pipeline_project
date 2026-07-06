"""
Инициализация Sentry для отслеживания ошибок в проде.

Если SENTRY_DSN не задан (например, в local/CI окружении) — инициализация
тихо пропускается, никаких ошибок при старте приложения.
"""
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def configure_sentry() -> None:
    settings = get_settings()

    if not settings.sentry_dsn:
        logger.info("sentry_disabled", reason="SENTRY_DSN not set")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(monitor_beat_tasks=False),
            LoggingIntegration(level=None, event_level="ERROR"),
        ],
    )
    logger.info("sentry_enabled", environment=settings.environment)

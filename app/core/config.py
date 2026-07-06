"""
Централизованная конфигурация приложения.

Все настройки читаются из переменных окружения (.env в локальной разработке,
реальные env vars в проде/контейнере). Никаких секретов в коде.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Общие настройки приложения ---
    app_name: str = "ai-shorts-pipeline"
    environment: Literal["local", "ci", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- База данных ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/shorts_pipeline"

    # --- Celery / Redis (брокер и backend результатов) ---
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    celery_task_time_limit_seconds: int = 60 * 30  # 30 минут — видео может резаться долго

    # --- LLM-провайдер (Strategy pattern, см. app.services.llm) ---
    llm_provider: Literal["openai", "anthropic", "fake"] = "fake"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # --- TTS (Edge TTS — бесплатный, голоса Microsoft Azure Neural) ---
    tts_provider: Literal["edge", "fake"] = "edge"
    edge_tts_voice: str = "ru-RU-DmitryNeural"
    edge_tts_rate: str = "+0%"
    edge_tts_volume: str = "+0%"

    # --- Хранилище файлов (абстракция StorageBackend) ---
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_root: Path = Path("/data/storage")
    s3_endpoint_url: str | None = None
    s3_bucket: str = "shorts-pipeline"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None

    # --- FFmpeg ---
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    target_video_width: int = 1080
    target_video_height: int = 1920  # вертикальный формат для Shorts/Reels

    # --- Subtitles extraction (whisper) ---
    whisper_model: str = "base"
    whisper_device: Literal["cpu", "cuda"] = "cpu"

    # --- Sentry ---
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.1

    # --- Prometheus ---
    prometheus_multiproc_dir: str | None = None

    # --- Логирование ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = True

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    """Кэшированный singleton настроек — читаем env один раз за процесс."""
    return Settings()

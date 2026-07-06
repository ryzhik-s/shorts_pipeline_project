"""Pydantic-схемы для входящих запросов и исходящих ответов API."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import JobStatus, PipelineStep


class JobCreateRequest(BaseModel):
    """Запрос на создание нового job: 'нарежь мне Shorts из этого видео'."""

    source_video_path: str = Field(
        ...,
        description="Путь/идентификатор исходного видео в storage backend",
        examples=["uploads/spongebob_s01e05.mp4"],
    )
    source_title: str | None = Field(
        default=None,
        description="Человекочитаемое название источника (для логов/UI)",
        examples=["SpongeBob S01E05 — Plankton's plan"],
    )
    target_duration_seconds: int = Field(
        default=55,
        ge=15,
        le=90,
        description="Целевая длительность готового Shorts-ролика в секундах",
    )


class StepRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step: PipelineStep
    status: JobStatus
    duration_seconds: float | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    current_step: PipelineStep | None
    source_video_path: str
    source_title: str | None
    target_duration_seconds: int
    error_message: str | None
    output_video_path: str | None
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime


class JobDetailResponse(JobResponse):
    """Подробный ответ с артефактами и историей шагов — для дебага/UI прогресса."""

    plot_analysis: dict | None
    script: dict | None
    timecodes: dict | None
    step_runs: list[StepRunResponse] = []


class JobCreateResponse(BaseModel):
    id: uuid.UUID
    status: JobStatus
    celery_task_id: str

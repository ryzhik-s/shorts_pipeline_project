"""
ORM-модели проекта (SQLAlchemy 2.0 style, async).

Job — одна "прогонка" видео через весь pipeline.
PipelineStepRun — лог выполнения каждого шага (для метрик/отладки/UI прогресса).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class PipelineStep(str, enum.Enum):
    EXTRACT_SUBTITLES = "extract_subtitles"
    ANALYZE_PLOT = "analyze_plot"
    WRITE_SCRIPT = "write_script"
    GENERATE_TIMECODES = "generate_timecodes"
    CUT_VIDEO = "cut_video"
    GENERATE_VOICEOVER = "generate_voiceover"
    BURN_SUBTITLES = "burn_subtitles"


class Job(Base):
    """Одна задача: 'превратить вот это длинное видео в Shorts'."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_video_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    target_duration_seconds: Mapped[int] = mapped_column(default=55)

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.PENDING, nullable=False
    )
    current_step: Mapped[PipelineStep | None] = mapped_column(
        Enum(PipelineStep, name="pipeline_step"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Артефакты пайплайна, накапливаемые по ходу выполнения
    subtitles: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    plot_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    script: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timecodes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cut_video_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    voiceover_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    output_video_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    step_runs: Mapped[list["PipelineStepRun"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="PipelineStepRun.started_at"
    )


class PipelineStepRun(Base):
    """
    Лог выполнения одного шага пайплайна для конкретного job.

    Используется и для отображения прогресса, и как источник данных
    для метрики длительности по шагам (Prometheus Histogram).
    """

    __tablename__ = "pipeline_step_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    step: Mapped[PipelineStep] = mapped_column(Enum(PipelineStep, name="pipeline_step"))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status"))
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="step_runs")

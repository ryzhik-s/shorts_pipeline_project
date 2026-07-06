"""initial schema: jobs, pipeline_step_runs

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-20

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

job_status_enum = postgresql.ENUM(
    "pending", "running", "success", "failed", name="job_status"
)
pipeline_step_enum = postgresql.ENUM(
    "extract_subtitles",
    "analyze_plot",
    "write_script",
    "generate_timecodes",
    "cut_video",
    "generate_voiceover",
    "burn_subtitles",
    name="pipeline_step",
)


def upgrade() -> None:
    job_status_enum.create(op.get_bind(), checkfirst=True)
    pipeline_step_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_video_path", sa.String(length=1024), nullable=False),
        sa.Column("source_title", sa.String(length=512), nullable=True),
        sa.Column("target_duration_seconds", sa.Integer(), nullable=False, server_default="55"),
        sa.Column(
            "status",
            job_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("current_step", pipeline_step_enum, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("subtitles", postgresql.JSONB(), nullable=True),
        sa.Column("plot_analysis", postgresql.JSONB(), nullable=True),
        sa.Column("script", postgresql.JSONB(), nullable=True),
        sa.Column("timecodes", postgresql.JSONB(), nullable=True),
        sa.Column("cut_video_path", sa.String(length=1024), nullable=True),
        sa.Column("voiceover_path", sa.String(length=1024), nullable=True),
        sa.Column("output_video_path", sa.String(length=1024), nullable=True),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "pipeline_step_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step", pipeline_step_enum, nullable=False),
        sa.Column("status", job_status_enum, nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_pipeline_step_runs_job_id", "pipeline_step_runs", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_step_runs_job_id", table_name="pipeline_step_runs")
    op.drop_table("pipeline_step_runs")
    op.drop_table("jobs")
    pipeline_step_enum.drop(op.get_bind(), checkfirst=True)
    job_status_enum.drop(op.get_bind(), checkfirst=True)

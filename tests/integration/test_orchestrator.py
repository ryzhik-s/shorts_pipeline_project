"""
End-to-end тест оркестратора пайплайна (app.pipeline.orchestrator.run_pipeline)
с полностью замоканными внешними зависимостями:
  - extract_subtitles -> мокируем (whisper не запускаем в тестах, слишком тяжело для CI)
  - LLM -> FakeLLMProvider
  - TTS -> FakeTTSProvider
  - ffmpeg -> мокируем asyncio.create_subprocess_exec

Цель теста — убедиться, что все 7 шагов пайплайна вызываются в правильном
порядке, статус job переходит pending -> running -> success, и каждый шаг
записывается в PipelineStepRun (для отображения прогресса и метрик).
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.db.models import Job, JobStatus, PipelineStep
from app.pipeline.orchestrator import run_pipeline
from app.services.llm.fake_provider import FakeLLMProvider
from app.services.storage.base import StorageBackend
from app.services.tts.fake_provider import FakeTTSProvider


class _FakeStorageBackend(StorageBackend):
    """Storage backend для теста — работает в tmp_path, не трогает реальный диск."""

    def __init__(self, root: Path):
        self._root = root

    def resolve_path(self, relative_path: str) -> Path:
        path = self._root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(b"fake source video bytes")
        return path

    def job_workspace(self, job_id: str) -> Path:
        workspace = self._root / "jobs" / job_id
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace


def _mock_subprocess_success():
    process = MagicMock()
    process.returncode = 0
    process.communicate = AsyncMock(return_value=(b"", b""))
    return process


@pytest.mark.asyncio
async def test_full_pipeline_completes_successfully(sample_job: Job, db_session, tmp_path, fake_subtitles):
    storage = _FakeStorageBackend(tmp_path)
    llm = FakeLLMProvider()
    tts = FakeTTSProvider()

    with (
        patch(
            "app.pipeline.orchestrator.extract_subtitles", return_value=fake_subtitles
        ) as mock_extract,
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=_mock_subprocess_success()),
        ),
    ):
        await run_pipeline(
            db=db_session,
            job=sample_job,
            llm=llm,
            tts=tts,
            storage=storage,
            llm_provider_name="fake",
        )

    mock_extract.assert_called_once()

    await db_session.refresh(sample_job)
    assert sample_job.status == JobStatus.SUCCESS
    assert sample_job.current_step is None
    assert sample_job.output_video_path is not None
    assert sample_job.subtitles == fake_subtitles
    assert sample_job.plot_analysis is not None
    assert sample_job.script is not None
    assert sample_job.timecodes is not None

    result = await db_session.execute(
        select(Job).where(Job.id == sample_job.id)
    )
    job_from_db = result.scalar_one()
    assert job_from_db.status == JobStatus.SUCCESS


@pytest.mark.asyncio
async def test_pipeline_records_step_runs_for_all_steps(
    sample_job: Job, db_session, tmp_path, fake_subtitles
):
    from sqlalchemy.orm import selectinload

    storage = _FakeStorageBackend(tmp_path)
    llm = FakeLLMProvider()
    tts = FakeTTSProvider()

    with (
        patch("app.pipeline.orchestrator.extract_subtitles", return_value=fake_subtitles),
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=_mock_subprocess_success()),
        ),
    ):
        await run_pipeline(
            db=db_session,
            job=sample_job,
            llm=llm,
            tts=tts,
            storage=storage,
            llm_provider_name="fake",
        )

    result = await db_session.execute(
        select(Job).options(selectinload(Job.step_runs)).where(Job.id == sample_job.id)
    )
    job = result.scalar_one()

    completed_steps = {run.step for run in job.step_runs if run.status == JobStatus.SUCCESS}
    expected_steps = set(PipelineStep)

    assert completed_steps == expected_steps
    assert all(run.duration_seconds is not None for run in job.step_runs)


@pytest.mark.asyncio
async def test_pipeline_marks_job_as_failed_on_llm_error(
    sample_job: Job, db_session, tmp_path, fake_subtitles
):
    storage = _FakeStorageBackend(tmp_path)
    tts = FakeTTSProvider()

    broken_llm = AsyncMock()
    broken_llm.complete_json.side_effect = RuntimeError("LLM API недоступен")

    with patch("app.pipeline.orchestrator.extract_subtitles", return_value=fake_subtitles):
        with pytest.raises(RuntimeError, match="LLM API недоступен"):
            await run_pipeline(
                db=db_session,
                job=sample_job,
                llm=broken_llm,
                tts=tts,
                storage=storage,
                llm_provider_name="fake",
            )

    await db_session.refresh(sample_job)
    assert sample_job.status == JobStatus.FAILED
    assert "LLM API недоступен" in sample_job.error_message
    # Шаг, на котором всё упало, должен быть зафиксирован
    assert sample_job.current_step == PipelineStep.ANALYZE_PLOT

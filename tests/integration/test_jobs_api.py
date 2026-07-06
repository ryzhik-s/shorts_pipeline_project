"""
Integration-тесты для /api/v1/jobs.

Celery task .delay() мокируется (eager-выполнение Celery поднимает требования
к окружению до уровня e2e — в этих тестах нас интересует только HTTP-слой API:
правильно ли job создаётся/сериализуется/возвращается, а не фактическая
обработка видео, которая покрыта test_orchestrator.py).
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import Job, JobStatus


@pytest.fixture(autouse=True)
def _mock_celery_delay():
    """Подменяем process_video_job.delay(), чтобы тесты не требовали запущенный Redis."""
    fake_task = MagicMock()
    fake_task.id = str(uuid.uuid4())

    with patch("app.api.routes.jobs.process_video_job.delay", return_value=fake_task) as mock:
        yield mock


@pytest.mark.asyncio
async def test_create_job_returns_201_and_pending_status(client: AsyncClient):
    response = await client.post(
        "/api/v1/jobs",
        json={
            "source_video_path": "uploads/spongebob_s01e05.mp4",
            "source_title": "SpongeBob S01E05",
            "target_duration_seconds": 50,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == JobStatus.PENDING.value
    assert "id" in body
    assert "celery_task_id" in body


@pytest.mark.asyncio
async def test_create_job_validates_target_duration_bounds(client: AsyncClient):
    response = await client.post(
        "/api/v1/jobs",
        json={"source_video_path": "uploads/video.mp4", "target_duration_seconds": 999},
    )

    assert response.status_code == 422  # вне диапазона 15..90, см. JobCreateRequest


@pytest.mark.asyncio
async def test_get_job_returns_404_for_unknown_id(client: AsyncClient):
    random_id = uuid.uuid4()
    response = await client.get(f"/api/v1/jobs/{random_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_job_returns_full_details(client: AsyncClient, db_session):
    create_response = await client.post(
        "/api/v1/jobs", json={"source_video_path": "uploads/video.mp4"}
    )
    job_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == job_id
    assert body["status"] == JobStatus.PENDING.value
    assert body["step_runs"] == []


@pytest.mark.asyncio
async def test_list_jobs_returns_created_jobs_ordered_by_recency(client: AsyncClient):
    await client.post("/api/v1/jobs", json={"source_video_path": "uploads/a.mp4"})
    await client.post("/api/v1/jobs", json={"source_video_path": "uploads/b.mp4"})

    response = await client.get("/api/v1/jobs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    # Самый свежий job (b.mp4) должен быть первым
    assert body[0]["source_video_path"] == "uploads/b.mp4"


@pytest.mark.asyncio
async def test_create_job_persists_celery_task_id(client: AsyncClient, db_session):
    response = await client.post(
        "/api/v1/jobs", json={"source_video_path": "uploads/video.mp4"}
    )
    job_id = response.json()["id"]

    result = await db_session.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = result.scalar_one()

    assert job.celery_task_id is not None

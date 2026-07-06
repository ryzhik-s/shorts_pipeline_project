"""
Тест Celery-задачи process_video_job в eager-режиме (синхронное выполнение
без реального брокера/воркера — стандартный подход pytest-celery для unit-тестов
бизнес-логики таски, без необходимости в Redis).

Полный E2E пайплайн внутри задачи мокируется (он уже покрыт test_orchestrator.py) —
здесь нас интересует именно слой Celery: что задача с правильным job_id
действительно запускается и возвращает job_id при успехе.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.workers.celery_app import celery_app
from app.workers.tasks import process_video_job


@pytest.fixture(autouse=True)
def _celery_eager_mode():
    """В eager-режиме .delay()/.apply_async() выполняются синхронно в текущем процессе."""
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
    yield
    celery_app.conf.update(task_always_eager=False)


def test_process_video_job_runs_async_pipeline_and_returns_job_id():
    fake_job_id = "11111111-1111-1111-1111-111111111111"

    with patch(
        "app.workers.tasks._process_video_job_async", new=AsyncMock(return_value=None)
    ) as mock_pipeline:
        result = process_video_job.apply(args=[fake_job_id]).get()

    mock_pipeline.assert_called_once_with(fake_job_id)
    assert result == fake_job_id


def test_process_video_job_retries_on_failure():
    fake_job_id = "22222222-2222-2222-2222-222222222222"

    with patch(
        "app.workers.tasks._process_video_job_async",
        new=AsyncMock(side_effect=RuntimeError("временный сбой БД")),
    ):
        async_result = process_video_job.apply(args=[fake_job_id])

        # В eager+propagates режиме исключение из retry всплывает наружу как Retry/исходное.
        with pytest.raises(Exception):
            async_result.get()

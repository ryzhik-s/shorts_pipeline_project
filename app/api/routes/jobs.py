"""
API роуты для управления job'ами обработки видео.

POST /api/v1/jobs       — создать новый job (запускает Celery task)
GET  /api/v1/jobs/{id}  — получить статус/результат job'а
GET  /api/v1/jobs       — список job'ов (с пагинацией)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.db.models import Job
from app.db.session import get_db_session
from app.schemas.job import JobCreateRequest, JobCreateResponse, JobDetailResponse, JobResponse
from app.workers.tasks import process_video_job

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreateRequest, db: AsyncSession = Depends(get_db_session)
) -> JobCreateResponse:
    """
    Создаёт новый job и асинхронно ставит его в очередь Celery на обработку.

    Ответ возвращается немедленно (job в статусе PENDING) — фактическая
    обработка видео (минуты) происходит в фоновом Celery worker.
    """
    job = Job(
        source_video_path=payload.source_video_path,
        source_title=payload.source_title,
        target_duration_seconds=payload.target_duration_seconds,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = process_video_job.delay(str(job.id))
    job.celery_task_id = task.id
    await db.commit()

    logger.info("job_created", job_id=str(job.id), celery_task_id=task.id)

    return JobCreateResponse(id=job.id, status=job.status, celery_task_id=task.id)


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> JobDetailResponse:
    """Возвращает подробный статус job'а, включая историю выполнения шагов."""
    result = await db.execute(
        select(Job).options(selectinload(Job.step_runs)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} не найден")

    return JobDetailResponse.model_validate(job)


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db_session)
) -> list[JobResponse]:
    """Список job'ов, отсортированный от новых к старым."""
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
    )
    jobs = result.scalars().all()
    return [JobResponse.model_validate(job) for job in jobs]

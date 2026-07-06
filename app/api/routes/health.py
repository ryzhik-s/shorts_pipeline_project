"""Health-check эндпоинт — для Docker healthcheck и k8s liveness/readiness probes."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)) -> dict:
    """Проверяет доступность сервиса и подключения к БД."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}

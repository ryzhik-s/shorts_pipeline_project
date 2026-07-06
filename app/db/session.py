"""
Async SQLAlchemy engine + сессии.

Используем async engine, потому что FastAPI-обработчики, читающие статус job,
должны быть неблокирующими, даже если тяжёлая работа выполняется в Celery.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — отдаёт сессию и гарантированно её закрывает."""
    async with AsyncSessionLocal() as session:
        yield session

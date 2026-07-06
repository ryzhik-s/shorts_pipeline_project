"""
Общие pytest-фикстуры.

Тесты используют:
  - SQLite in-memory (aiosqlite) вместо Postgres — быстро, без внешних зависимостей,
    схема совпадает достаточно для unit/integration тестов API-слоя.
  - FakeLLMProvider / FakeTTSProvider — без сетевых вызовов и без платных API.
  - httpx.AsyncClient с ASGITransport — тестируем FastAPI-приложение без реального сервера.

Переменные окружения для тестового режима выставлены в pyproject.toml ([tool.pytest.ini_options]).
"""
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import Job, JobStatus
from app.db.session import Base, get_db_session
from app.main import app


@pytest_asyncio.fixture
async def db_engine():
    """In-memory SQLite engine, живёт ровно один тест."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Тестовый HTTP-клиент с подменённой зависимостью БД (in-memory SQLite)."""

    async def _override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_job(db_session: AsyncSession) -> Job:
    """Job в статусе PENDING, готовый к использованию в тестах оркестратора."""
    job = Job(
        id=uuid.uuid4(),
        source_video_path="uploads/sample.mp4",
        source_title="Sample Episode",
        target_duration_seconds=55,
        status=JobStatus.PENDING,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest.fixture
def fake_subtitles() -> dict:
    return {
        "segments": [
            {"start": 0.0, "end": 4.0, "text": "Мистер Крабс решил сэкономить на патти."},
            {"start": 4.0, "end": 9.0, "text": "Постоянные клиенты заметили подмену."},
            {"start": 9.0, "end": 14.0, "text": "Крабс вернул старый рецепт и извинился."},
        ],
        "language": "ru",
    }

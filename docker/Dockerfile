# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# ffmpeg — для нарезки видео и вшивания субтитров.
# libsndfile1 — нужен faster-whisper/audio-зависимостям для декодирования аудио.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# --- Стадия для тестов/CI: добавляет dev-зависимости ---
FROM base AS test
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
COPY pyproject.toml ./

# --- Финальная продакшен-стадия API ---
FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Финальная продакшен-стадия Celery worker ---
FROM base AS worker
CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]

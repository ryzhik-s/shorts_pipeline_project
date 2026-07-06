.PHONY: help up down logs test lint format migrate shell-api shell-db build

COMPOSE = docker compose -f docker/docker-compose.yml

help:
	@echo "Доступные команды:"
	@echo "  make up          — поднять весь стек (api, worker, db, redis, prometheus, grafana, flower)"
	@echo "  make down        — остановить и удалить контейнеры"
	@echo "  make logs        — хвост логов всех сервисов"
	@echo "  make test        — прогнать тесты локально (без Docker)"
	@echo "  make test-docker — прогнать тесты внутри Docker-образа test-стадии"
	@echo "  make lint        — ruff + mypy"
	@echo "  make format      — автоформатирование ruff"
	@echo "  make migrate     — применить миграции Alembic"
	@echo "  make revision    — создать новую миграцию (make revision m=\"описание\")"
	@echo "  make shell-api   — bash внутри контейнера api"
	@echo "  make build       — пересобрать Docker-образы"

up:
	$(COMPOSE) up -d --build
	@echo "API:        http://localhost:8000/docs"
	@echo "Flower:     http://localhost:5555"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana:    http://localhost:3000 (admin/admin)"

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

build:
	$(COMPOSE) build

test:
	ENVIRONMENT=ci LLM_PROVIDER=fake TTS_PROVIDER=fake pytest -v --cov=app --cov-report=term-missing

test-docker:
	docker build -f docker/Dockerfile --target test -t shorts-pipeline-test .
	docker run --rm \
		-e ENVIRONMENT=ci -e LLM_PROVIDER=fake -e TTS_PROVIDER=fake \
		shorts-pipeline-test pytest -v --cov=app

lint:
	ruff check app tests
	mypy app

format:
	ruff format app tests
	ruff check --fix app tests

migrate:
	$(COMPOSE) run --rm api alembic upgrade head

revision:
	$(COMPOSE) run --rm api alembic revision --autogenerate -m "$(m)"

shell-api:
	$(COMPOSE) exec api bash

shell-db:
	$(COMPOSE) exec db psql -U postgres -d shorts_pipeline

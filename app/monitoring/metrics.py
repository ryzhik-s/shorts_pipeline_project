"""
Prometheus-метрики приложения.

Метрики разделены на:
  - HTTP-метрики (стандартные, через prometheus-fastapi-instrumentator)
  - Pipeline-метрики (кастомные, бизнес-специфичные для видео-обработки)
  - Celery-метрики (длительность задач, размер очереди)

Все метрики экспортируются на /metrics и собираются Prometheus,
визуализируются в Grafana (см. grafana/dashboards/).
"""
from prometheus_client import Counter, Gauge, Histogram

# --- Метрики на уровне всего job (видео -> Shorts) ---

JOB_PROCESSING_DURATION = Histogram(
    "shorts_job_processing_duration_seconds",
    "Полное время обработки одного видео от старта job до готового Shorts",
    buckets=(5, 15, 30, 60, 120, 300, 600, 1200, 1800),
)

JOBS_TOTAL = Counter(
    "shorts_jobs_total",
    "Количество job'ов по итоговому статусу",
    labelnames=("status",),  # success | failed
)

JOBS_IN_PROGRESS = Gauge(
    "shorts_jobs_in_progress",
    "Количество job'ов, находящихся в обработке прямо сейчас",
)

# --- Метрики по отдельным шагам pipeline ---

PIPELINE_STEP_DURATION = Histogram(
    "shorts_pipeline_step_duration_seconds",
    "Длительность выполнения одного шага пайплайна",
    labelnames=("step",),
    buckets=(1, 5, 15, 30, 60, 120, 300, 600),
)

PIPELINE_STEP_FAILURES = Counter(
    "shorts_pipeline_step_failures_total",
    "Количество ошибок по шагам пайплайна",
    labelnames=("step",),
)

# --- Метрики внешних интеграций (LLM/TTS) — полезно для контроля cost/latency ---

LLM_REQUEST_DURATION = Histogram(
    "shorts_llm_request_duration_seconds",
    "Длительность запроса к LLM-провайдеру",
    labelnames=("provider",),
    buckets=(0.5, 1, 2, 5, 10, 20, 40),
)

LLM_REQUEST_FAILURES = Counter(
    "shorts_llm_request_failures_total",
    "Количество неудачных запросов к LLM-провайдеру",
    labelnames=("provider",),
)

TTS_REQUEST_DURATION = Histogram(
    "shorts_tts_request_duration_seconds",
    "Длительность синтеза речи",
    labelnames=("provider",),
    buckets=(0.5, 1, 2, 5, 10, 20),
)

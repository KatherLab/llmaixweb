# backend/src/celery/celery_config.py
from __future__ import annotations

from kombu import Queue
from celery import Celery

from ..core.config import settings

# ───────────────────────── Celery app ──────────────────────────
celery_app: Celery | None = None

if not settings.DISABLE_CELERY:
    celery_app = Celery(
        "tasks",
        broker=settings.CELERY_BROKER_URL,
        include=[
            "backend.src.celery.preprocessing",
            "backend.src.celery.info_extraction",
        ],
    )

    # — Global safety & broker options —
    celery_app.conf.update(
        task_acks_late=True,                     # ACK after the task has succeeded
        task_reject_on_worker_lost=True,         # mark FAILURE if worker seg‑faults / OOMs
        broker_transport_options={
            "visibility_timeout": 3600,          # re‑queue an un‑acked msg after 1h
        },
        worker_prefetch_multiplier=1,            # one job at a time per child process
    )

    # — Queues —
    celery_app.conf.task_default_queue = "default"
    celery_app.conf.task_queues = (
        Queue("default"),
        Queue("preprocess"),                     # heavy OCR / preprocessing pipeline
    )

    # Import signal handlers once the app is ready
    from . import task_signals  # noqa: E402  (must come after celery_app is defined)

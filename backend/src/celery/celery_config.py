# backend/src/celery/celery_config.py
from __future__ import annotations

from celery import Celery
from kombu import Queue

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
        task_acks_late=True,  # ACK after the task has succeeded
        task_reject_on_worker_lost=True,  # mark FAILURE if worker seg‑faults / OOMs
        # Must be strictly greater than task_time_limit below: with Redis
        # transport the broker re-queues any un-acked message once this elapses.
        # If it's shorter than the hard time limit, a long-but-legitimate task
        # gets redelivered to a second worker while the original is still
        # running → double execution (duplicate LLM calls, duplicate docs,
        # status flaps). 8h comfortably exceeds the 6h+100s hard limit.
        broker_transport_options={
            "visibility_timeout": 28800,  # re‑queue an un‑acked msg after 8h
        },
        worker_prefetch_multiplier=1,  # one job at a time per child process
        # Hard backstop against runaway / hung tasks. Generous (6h) so it never
        # false-kills a legitimate long batch; the per-call timeouts (LLM/OCR)
        # and the periodic stuck-task sweeper catch real hangs far earlier.
        # SoftTimeLimitExceeded is an Exception, so the trial task's top-level
        # try/except finalizes it as FAILED; preprocessing handles it per-file.
        task_soft_time_limit=21600,  # 6 hours
        task_time_limit=21700,  # 6h + 100s (hard kill)
    )

    # — Queues —
    celery_app.conf.task_default_queue = "default"
    celery_app.conf.task_queues = (
        Queue("default"),
        Queue("preprocess"),  # heavy OCR / preprocessing pipeline
    )

    # Route Celery's logging through our centralized config so worker logs use
    # the same format (and JSON option) as the web process. Connecting a
    # receiver to ``setup_logging`` tells Celery not to install its own
    # handlers, giving us a single, consistent logging setup across processes.
    from celery.signals import setup_logging as _celery_setup_logging

    @_celery_setup_logging.connect
    def _configure_celery_logging(**_kwargs):
        from ..utils.logging_config import setup_logging

        setup_logging(level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

    # Import signal handlers + periodic sweeper once the app is ready. This
    # must run inside the `not DISABLE_CELERY` guard: task_signals registers
    # `@celery_app.task` / `@celery_app.on_after_configure` decorators at
    # import time, which would crash if `celery_app` were None.
    from . import task_signals  # noqa: E402, F401

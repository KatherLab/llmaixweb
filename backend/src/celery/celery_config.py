# celery_config.py
from ..core.config import settings

if not settings.DISABLE_CELERY:
    from celery import Celery

    celery_app = Celery(
        "tasks",
        broker="redis://localhost:6379/0",
        include=[
            "backend.src.celery.preprocessing",
            "backend.src.celery.info_extraction",
        ],
    )
else:
    celery_app = None

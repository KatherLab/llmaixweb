# backend/src/core/rate_limit.py
"""Shared slowapi rate limiter.

A single :class:`Limiter` instance shared by ``main.py`` (for the exception
handler / app state) and the auth/user routers (for the ``@limiter.limit``
decorators). Centralizing it here ensures every rate-limited endpoint backs
its counters with the same storage.

Storage backend selection:
  * If the Celery broker is Redis (the common deployment), counters live in
    Redis so they are shared across all Uvicorn/gunicorn workers — without
    this, each process keeps its own in-memory counters and an attacker gets
    ``N × limit`` attempts under horizontal scaling.
  * Otherwise (e.g. tests, or a non-Redis broker) fall back to in-memory
    storage. This is also the safe default when Redis is unreachable at
    import time: slowapi will raise on the first limited request if a Redis
    URI is configured but unreachable, which would break login entirely.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings


def _storage_uri() -> str:
    """Pick the rate-limit storage backend.

    Prefer Redis (shared across workers) when the broker is Redis AND it's
    reachable; otherwise fall back to in-memory. We probe connectivity rather
    than blindly returning the Redis URI because slowapi connects lazily on
    the first limited request — if Redis were configured but down, that would
    turn a Redis outage into a total login outage (the limiter raises instead
    of degrading). Falling back to memory keeps rate limiting best-effort,
    matching how the rest of the app treats Redis as optional.
    """
    broker_url = settings.CELERY_BROKER_URL or ""
    if broker_url.startswith("redis://"):
        try:
            import redis

            client = redis.from_url(
                broker_url,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
                retry_on_timeout=False,
            )
            client.ping()
            return broker_url
        except Exception:
            # Redis configured but unreachable — don't let that break login.
            return "memory://"
    return "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=_storage_uri(),
)

# backend/src/utils/redis_broadcast.py
"""Redis pub/sub for broadcasting task updates from Celery workers to FastAPI."""

import json
import logging
import threading
import time
from typing import Any

import redis

from ..core.config import settings

logger = logging.getLogger(__name__)

# Redis channel for task updates
TASK_UPDATE_CHANNEL = "task_updates"

# Redis channel for runtime-settings cache invalidation. When an admin
# changes a setting via the web process, a message here tells Celery worker
# processes (separate processes with their own @lru_cache'd get_settings())
# to drop and reload their cached settings — otherwise worker config is stale
# until process restart (e.g. an OCR engine disabled for privacy would keep
# running in workers).
SETTINGS_INVALIDATE_CHANNEL = "settings_invalidate"

# Shared publisher client (lazily initialized). Creating a fresh
# redis.from_url() client + connection pool on every broadcast (the heartbeat
# publishes every ~3s per active task) churns connections and can exhaust
# Redis/file-descriptor limits under concurrent task load — which would also
# break the Celery broker transport. Reuse one client per process instead.
_redis_client: redis.Redis | None = None
_redis_client_lock = threading.Lock()
_redis_client_unavailable = object()  # sentinel: we tried and Redis is down
_redis_client_state: Any = None
# Monotonic timestamp at which the "unavailable" sentinel was set. We retry
# connecting after this many seconds so a Redis that comes back online is
# picked up without a process restart. Without this, the unavailable state
# was cached forever (a transient Redis outage permanently disabled pub/sub).
_REDIS_RETRY_SECONDS = 30.0
_redis_unavailable_at: float = 0.0


def _new_redis_client() -> redis.Redis | None:
    """Create a single Redis client (or None if Redis is unavailable)."""
    broker_url = settings.CELERY_BROKER_URL
    if not broker_url.startswith("redis://"):
        return None
    try:
        # Short timeouts so a missing Redis never blocks task processing.
        client = redis.from_url(
            broker_url,
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
            retry_on_timeout=False,
        )
        client.ping()
        return client
    except Exception as e:
        logger.debug(f"Redis not available: {e}")
        return None


def get_redis_client() -> redis.Redis | None:
    """Return the shared Redis client for pub/sub, creating it on first use.

    Returns None if Redis is unavailable (cached so we don't retry-connect on
    every heartbeat tick, but re-checked after ``_REDIS_RETRY_SECONDS`` so a
    Redis that recovers is picked up without a restart). The returned client
    is shared and must NOT be closed by callers — it lives for the process.
    For a client you intend to close yourself (e.g. a long-lived subscriber),
    use :func:`new_dedicated_redis_client`.
    """
    global _redis_client, _redis_client_state, _redis_unavailable_at
    if _redis_client is not None:
        return _redis_client
    if _redis_client_state is _redis_client_unavailable and (
        time.monotonic() - _redis_unavailable_at < _REDIS_RETRY_SECONDS
    ):
        return None
    with _redis_client_lock:
        # Re-check inside the lock: another thread may have initialized it.
        if _redis_client is not None:
            return _redis_client
        if _redis_client_state is _redis_client_unavailable and (
            time.monotonic() - _redis_unavailable_at < _REDIS_RETRY_SECONDS
        ):
            return None
        client = _new_redis_client()
        if client is None:
            _redis_client_state = _redis_client_unavailable
            _redis_unavailable_at = time.monotonic()
            return None
        _redis_client = client
        return _redis_client


def new_dedicated_redis_client() -> redis.Redis | None:
    """Create a fresh, independently-owned Redis client (caller closes it).

    Used by the FastAPI subscriber, which needs its own client so that closing
    it on shutdown doesn't tear down the shared publisher client.
    """
    return _new_redis_client()


def _publish(message: dict[str, Any], label: str) -> bool:
    client = get_redis_client()
    if not client:
        logger.debug(f"Redis client not available for {label} pub/sub")
        return False
    try:
        client.publish(TASK_UPDATE_CHANNEL, json.dumps(message))
        return True
    except Exception as e:
        logger.error(f"Failed to publish {label} update: {e}")
        # Reset the shared client so the next call re-connects after a
        # transient failure (e.g. Redis restarted).
        _reset_redis_client()
        return False


def _reset_redis_client() -> None:
    """Drop the cached shared client so the next call re-connects."""
    global _redis_client, _redis_client_state
    with _redis_client_lock:
        old = _redis_client
        _redis_client = None
        _redis_client_state = None
    if old is not None:
        try:
            old.close()
        except Exception:
            pass


def publish_task_update(message: dict[str, Any]) -> bool:
    """
    Publish a task update message via Redis pub/sub.

    Args:
        message: Dictionary containing task update data

    Returns:
        True if message was published successfully, False otherwise
    """
    return _publish(message, "task")


def subscribe_task_updates():
    """
    Subscribe to task update messages from Redis pub/sub.

    Returns a pubsub object that can be used to listen for messages.
    Caller is responsible for calling unsubscribe() when done.
    """
    client = new_dedicated_redis_client()
    if not client:
        return None

    try:
        pubsub = client.pubsub()
        pubsub.subscribe(TASK_UPDATE_CHANNEL)
        return pubsub
    except Exception as e:
        logger.error(f"Failed to subscribe to task updates: {e}")
        try:
            client.close()
        except Exception:
            pass
        return None


def publish_trial_update(message: dict) -> bool:
    """
    Publish a trial update message via Redis pub/sub.

    Args:
        message: Dictionary containing trial update data

    Returns:
        True if message was published successfully, False otherwise
    """
    return _publish(message, "trial")


def publish_settings_invalidate() -> bool:
    """Notify all processes (esp. Celery workers) to reload cached settings.

    Called from the web process after an admin updates a runtime setting.
    Workers subscribe via :func:`subscribe_settings_invalidate` (set up in
    task_signals.py on worker_process_init) and call reload_settings_cache()
    locally. Best-effort: if Redis is down, workers simply stay stale until
    their next restart — same as before this mechanism existed.
    """
    return _publish({"type": "settings_invalidate"}, "settings_invalidate")


def subscribe_settings_invalidate():
    """Return a pubsub subscribed to the settings-invalidation channel.

    Uses a dedicated client (caller owns it and must close it). Returns None
    if Redis is unavailable.
    """
    client = new_dedicated_redis_client()
    if not client:
        return None
    try:
        pubsub = client.pubsub()
        pubsub.subscribe(SETTINGS_INVALIDATE_CHANNEL)
        return pubsub
    except Exception as e:
        logger.error(f"Failed to subscribe to settings invalidate: {e}")
        try:
            client.close()
        except Exception:
            pass
        return None

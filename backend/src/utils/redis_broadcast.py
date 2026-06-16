# backend/src/utils/redis_broadcast.py
"""Redis pub/sub for broadcasting task updates from Celery workers to FastAPI."""

import json
import logging
from typing import Any

import redis

from ..core.config import settings

logger = logging.getLogger(__name__)

# Redis channel for task updates
TASK_UPDATE_CHANNEL = "task_updates"


def get_redis_client() -> redis.Redis | None:
    """Get Redis client for pub/sub."""
    try:
        # Parse Redis URL from Celery broker config
        broker_url = settings.CELERY_BROKER_URL
        if broker_url.startswith("redis://"):
            # Use short timeouts to avoid blocking on startup
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


def publish_task_update(message: dict[str, Any]) -> bool:
    """
    Publish a task update message via Redis pub/sub.

    Args:
        message: Dictionary containing task update data

    Returns:
        True if message was published successfully, False otherwise
    """
    client = get_redis_client()
    if not client:
        logger.debug("Redis client not available for pub/sub")
        return False

    try:
        client.publish(TASK_UPDATE_CHANNEL, json.dumps(message))
        return True
    except Exception as e:
        logger.error(f"Failed to publish task update: {e}")
        return False


def subscribe_task_updates():
    """
    Subscribe to task update messages from Redis pub/sub.

    Returns a pubsub object that can be used to listen for messages.
    Caller is responsible for calling unsubscribe() when done.
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        pubsub = client.pubsub()
        pubsub.subscribe(TASK_UPDATE_CHANNEL)
        return pubsub
    except Exception as e:
        logger.error(f"Failed to subscribe to task updates: {e}")
        return None


def publish_trial_update(message: dict) -> bool:
    """
    Publish a trial update message via Redis pub/sub.

    Args:
        message: Dictionary containing trial update data

    Returns:
        True if message was published successfully, False otherwise
    """
    client = get_redis_client()
    if not client:
        logger.debug("Redis client not available for trial pub/sub")
        return False

    try:
        client.publish(TASK_UPDATE_CHANNEL, json.dumps(message))
        return True
    except Exception as e:
        logger.error(f"Failed to publish trial update: {e}")
        return False

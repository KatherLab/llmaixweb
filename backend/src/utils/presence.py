# backend/src/utils/presence.py
"""Who currently has the app open, shared across processes via Redis.

The "only notify me when I'm away" preference needs an answer to *is this user
looking at the app right now?* — asked from a Celery worker, while the answer is
only known to the web process holding the WebSocket. So the web process writes a
short-lived marker per connected user and the worker reads it.

Design notes:

* One key per user (``presence:user:<id>``) with a TTL, refreshed by the client
  heartbeat. A user with several tabs open shares one key; it is deleted when the
  *last* of their sockets goes away (``ConnectionManager`` owns that count).
* The TTL is what makes this correct rather than merely optimistic: a browser
  that vanishes without closing the socket (laptop suspended, network dropped)
  stops heartbeating, and the key expires on its own. The cost is a window of up
  to ``NOTIFY_PRESENCE_TTL_SECONDS`` in which such a user still counts as
  present and a job-finished email is suppressed.
* Redis unavailable (or a non-Redis broker) means *no* presence information. We
  then report "away", because the failure mode of sending an email the user
  didn't strictly need beats silently swallowing the one they were waiting for.
* Multi-process web deployments share the key, so a second worker holding
  another tab open would have its presence cleared when the first process sees
  its own last socket close. The WebSocket layer already assumes a single web
  process (``ConnectionManager`` is in-memory), so this is not a new constraint —
  but it is the thing to fix first if that assumption ever changes.
"""

import logging

from .redis_broadcast import get_redis_client

logger = logging.getLogger(__name__)

_KEY_PREFIX = "presence:user:"


def _key(user_id: int) -> str:
    return f"{_KEY_PREFIX}{user_id}"


def _ttl() -> int:
    # Imported here, not at module scope: `websocket_manager` imports this module
    # at import time, and pulling in dynamic_settings would construct the DB
    # engine as a side effect of importing the WebSocket layer.
    from ..core.dynamic_settings import get_settings

    return max(30, int(get_settings().NOTIFY_PRESENCE_TTL_SECONDS))


def mark_online(user_id: int) -> None:
    """Record (or refresh) the user as present. Best-effort; never raises."""
    client = get_redis_client()
    if client is None:
        return
    try:
        client.setex(_key(user_id), _ttl(), b"1")
    except Exception as e:
        logger.debug("Could not mark user %s online: %s", user_id, e)


# Refreshing and first-marking are the same write; the alias exists so call
# sites read as what they mean (a heartbeat is not a connection).
touch = mark_online


def mark_offline(user_id: int) -> None:
    """Clear the user's presence marker. Best-effort; never raises.

    Call this only when the user's *last* socket closes — otherwise closing one
    of several tabs would report them away.
    """
    client = get_redis_client()
    if client is None:
        return
    try:
        client.delete(_key(user_id))
    except Exception as e:
        logger.debug("Could not mark user %s offline: %s", user_id, e)


def is_online(user_id: int) -> bool:
    """Whether the user has a live WebSocket connection.

    Returns False when presence cannot be determined (no Redis), which callers
    should read as "assume away, send the notification".
    """
    client = get_redis_client()
    if client is None:
        return False
    try:
        return bool(client.exists(_key(user_id)))
    except Exception as e:
        logger.debug("Could not read presence for user %s: %s", user_id, e)
        return False

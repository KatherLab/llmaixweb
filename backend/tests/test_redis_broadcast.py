# backend/tests/test_redis_broadcast.py
"""Unit tests for ``utils/redis_broadcast.py`` (Redis pub/sub broadcast).

``redis.from_url`` and the ``settings`` proxy are mocked so nothing touches a
real Redis. This module keeps **mutable module-global state** (the cached
client, its "unavailable" sentinel state, and the unavailable-at timestamp),
so an autouse fixture resets all three globals *before and after* every test to
stop state leaking between tests.

Covers:
* non-``redis://`` broker early-return (publish is a no-op returning False),
* happy path where ``from_url(...).ping()`` succeeds and ``.publish()`` fires
  for ``publish_task_update`` / ``publish_trial_update`` /
  ``publish_settings_invalidate`` (incl. correct channel),
* client caching (``from_url`` called once across repeated publishes),
* the unavailable path (``ping()`` raises -> cached unavailable) and the 30s
  retry window (via patching ``time.monotonic``), and
* ``_publish`` returning False and resetting the client when ``publish()`` raises.
"""

import json
from unittest.mock import MagicMock

import pytest

from backend.src.core import config
from backend.src.utils import redis_broadcast as rb


# --------------------------------------------------------------------------- #
# Global-state reset (autouse) — before AND after every test.
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _reset_module_globals():
    def _reset():
        rb._redis_client = None
        rb._redis_client_state = None
        rb._redis_unavailable_at = 0.0

    _reset()
    yield
    _reset()


@pytest.fixture
def settings_inst():
    return config._get_settings()


@pytest.fixture
def redis_broker(monkeypatch, settings_inst):
    """Ensure the broker URL is a ``redis://`` URL (the pub/sub-enabled path)."""
    monkeypatch.setattr(settings_inst, "CELERY_BROKER_URL", "redis://localhost:6379/0")
    return settings_inst


@pytest.fixture
def mock_from_url(monkeypatch):
    """Patch ``redis.from_url`` to return a healthy MagicMock client.

    Returns (from_url_mock, client_mock). ``client.ping()`` succeeds and
    ``client.publish()`` is a MagicMock by default.
    """
    client = MagicMock(name="redis_client")
    from_url = MagicMock(name="from_url", return_value=client)
    monkeypatch.setattr(rb.redis, "from_url", from_url)
    return from_url, client


# --------------------------------------------------------------------------- #
# Non-redis broker early-return
# --------------------------------------------------------------------------- #
class TestNonRedisBroker:
    def test_new_client_returns_none_for_amqp(self, monkeypatch, settings_inst):
        monkeypatch.setattr(settings_inst, "CELERY_BROKER_URL", "amqp://guest@rabbit//")
        from_url = MagicMock()
        monkeypatch.setattr(rb.redis, "from_url", from_url)
        assert rb._new_redis_client() is None
        from_url.assert_not_called()

    def test_publish_is_noop_for_non_redis_broker(self, monkeypatch, settings_inst):
        monkeypatch.setattr(settings_inst, "CELERY_BROKER_URL", "memory://")
        from_url = MagicMock()
        monkeypatch.setattr(rb.redis, "from_url", from_url)
        assert rb.publish_task_update({"a": 1}) is False
        from_url.assert_not_called()


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #
class TestHappyPath:
    def test_get_redis_client_pings_and_caches(self, redis_broker, mock_from_url):
        from_url, client = mock_from_url
        got = rb.get_redis_client()
        assert got is client
        client.ping.assert_called_once()
        assert rb._redis_client is client

    def test_publish_task_update(self, redis_broker, mock_from_url):
        _, client = mock_from_url
        assert rb.publish_task_update({"task": 7}) is True
        client.publish.assert_called_once()
        channel, payload = client.publish.call_args.args
        assert channel == rb.TASK_UPDATE_CHANNEL
        assert json.loads(payload) == {"task": 7}

    def test_publish_trial_update(self, redis_broker, mock_from_url):
        _, client = mock_from_url
        assert rb.publish_trial_update({"trial": 3}) is True
        channel, payload = client.publish.call_args.args
        assert channel == rb.TASK_UPDATE_CHANNEL
        assert json.loads(payload) == {"trial": 3}

    def test_publish_settings_invalidate_uses_dedicated_channel(
        self, redis_broker, mock_from_url
    ):
        _, client = mock_from_url
        assert rb.publish_settings_invalidate() is True
        channel, payload = client.publish.call_args.args
        assert channel == rb.SETTINGS_INVALIDATE_CHANNEL
        assert json.loads(payload) == {"type": "settings_invalidate"}


# --------------------------------------------------------------------------- #
# Client caching
# --------------------------------------------------------------------------- #
class TestClientCaching:
    def test_from_url_called_once_across_publishes(self, redis_broker, mock_from_url):
        from_url, client = mock_from_url
        rb.publish_task_update({"a": 1})
        rb.publish_trial_update({"b": 2})
        rb.publish_settings_invalidate()
        from_url.assert_called_once()
        assert client.publish.call_count == 3

    def test_get_redis_client_returns_cached_instance(
        self, redis_broker, mock_from_url
    ):
        from_url, _ = mock_from_url
        a = rb.get_redis_client()
        b = rb.get_redis_client()
        assert a is b
        from_url.assert_called_once()


# --------------------------------------------------------------------------- #
# Unavailable path + retry window
# --------------------------------------------------------------------------- #
class TestUnavailablePath:
    def test_ping_failure_caches_unavailable(self, redis_broker, monkeypatch):
        client = MagicMock()
        client.ping.side_effect = Exception("connection refused")
        from_url = MagicMock(return_value=client)
        monkeypatch.setattr(rb.redis, "from_url", from_url)

        assert rb.get_redis_client() is None
        assert rb._redis_client is None
        assert rb._redis_client_state is rb._redis_client_unavailable

    def test_unavailable_is_cached_within_retry_window(self, redis_broker, monkeypatch):
        client = MagicMock()
        client.ping.side_effect = Exception("down")
        from_url = MagicMock(return_value=client)
        monkeypatch.setattr(rb.redis, "from_url", from_url)

        fake_time = {"t": 100.0}
        monkeypatch.setattr(rb.time, "monotonic", lambda: fake_time["t"])

        # First call: tries, fails, caches unavailable at t=100.
        assert rb.get_redis_client() is None
        assert from_url.call_count == 1

        # Within the 30s window: short-circuits without re-connecting.
        fake_time["t"] = 120.0  # +20s
        assert rb.get_redis_client() is None
        assert from_url.call_count == 1

    def test_retry_after_window_reconnects(self, redis_broker, monkeypatch):
        down = MagicMock()
        down.ping.side_effect = Exception("down")
        healthy = MagicMock()  # ping() ok

        from_url = MagicMock(side_effect=[down, healthy])
        monkeypatch.setattr(rb.redis, "from_url", from_url)

        fake_time = {"t": 100.0}
        monkeypatch.setattr(rb.time, "monotonic", lambda: fake_time["t"])

        assert rb.get_redis_client() is None
        assert from_url.call_count == 1

        # Past the retry window (+40s > 30s): reconnect and succeed.
        fake_time["t"] = 140.0
        assert rb.get_redis_client() is healthy
        assert from_url.call_count == 2

    def test_publish_returns_false_when_unavailable(self, redis_broker, monkeypatch):
        client = MagicMock()
        client.ping.side_effect = Exception("down")
        monkeypatch.setattr(rb.redis, "from_url", MagicMock(return_value=client))
        assert rb.publish_task_update({"a": 1}) is False


# --------------------------------------------------------------------------- #
# _publish resets client on publish failure
# --------------------------------------------------------------------------- #
class TestPublishFailureResets:
    def test_publish_error_returns_false_and_resets_client(
        self, redis_broker, monkeypatch
    ):
        client = MagicMock()
        client.publish.side_effect = Exception("broken pipe")
        from_url = MagicMock(return_value=client)
        monkeypatch.setattr(rb.redis, "from_url", from_url)

        assert rb.publish_task_update({"a": 1}) is False
        # Cached client dropped so the next call re-connects.
        assert rb._redis_client is None
        client.close.assert_called_once()

    def test_next_publish_reconnects_after_failure(self, redis_broker, monkeypatch):
        failing = MagicMock()
        failing.publish.side_effect = Exception("broken pipe")
        healthy = MagicMock()  # publish() ok

        from_url = MagicMock(side_effect=[failing, healthy])
        monkeypatch.setattr(rb.redis, "from_url", from_url)

        assert rb.publish_task_update({"a": 1}) is False
        assert rb.publish_task_update({"a": 2}) is True
        assert from_url.call_count == 2
        healthy.publish.assert_called_once()

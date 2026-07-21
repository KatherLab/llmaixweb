# backend/tests/test_websocket_manager.py
"""Unit tests for ``websocket_manager.ConnectionManager``.

``pytest-asyncio`` is NOT installed in this repo, so the async methods are
driven with ``asyncio.run(...)`` and the WebSocket is a ``unittest.mock``
``AsyncMock`` (its ``accept`` / ``send_json`` / ``close`` coroutines are
awaitable). Every test builds a FRESH ``ConnectionManager()`` so no state
leaks between tests (the module-level ``manager`` singleton is never touched).
"""

import asyncio
from unittest.mock import AsyncMock

from backend.src.websocket_manager import (
    MAX_CONNECTIONS_PER_USER,
    ConnectionManager,
    manager,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def make_ws():
    """A WebSocket double whose accept/send_json/close are awaitable."""
    return AsyncMock()


def connect(mgr, ws, user_id, is_admin=False, subprotocol=None):
    return asyncio.run(
        mgr.connect(ws, user_id, is_admin=is_admin, subprotocol=subprotocol)
    )


# --------------------------------------------------------------------------- #
# connect()
# --------------------------------------------------------------------------- #
class TestConnect:
    def test_happy_path_accepts_and_tracks(self):
        mgr = ConnectionManager()
        ws = make_ws()

        result = connect(mgr, ws, user_id=1)

        assert result is True
        ws.accept.assert_awaited_once()
        assert ws in mgr._active_connections[1]
        # Non-admin must not join the admin bucket.
        assert ws not in mgr._admin_connections

    def test_admin_connection_tracked_in_admin_bucket(self):
        mgr = ConnectionManager()
        ws = make_ws()

        connect(mgr, ws, user_id=7, is_admin=True)

        assert ws in mgr._active_connections[7]
        assert ws in mgr._admin_connections

    def test_subprotocol_echoed_in_accept(self):
        mgr = ConnectionManager()
        ws = make_ws()

        connect(mgr, ws, user_id=1, subprotocol="auth.token.abc")

        ws.accept.assert_awaited_once_with(subprotocol="auth.token.abc")

    def test_default_subprotocol_is_none(self):
        mgr = ConnectionManager()
        ws = make_ws()

        connect(mgr, ws, user_id=1)

        ws.accept.assert_awaited_once_with(subprotocol=None)

    def test_multiple_connections_same_user(self):
        mgr = ConnectionManager()
        a, b = make_ws(), make_ws()

        connect(mgr, a, user_id=1)
        connect(mgr, b, user_id=1)

        assert mgr._active_connections[1] == {a, b}

    def test_connection_cap_rejects_over_limit(self):
        mgr = ConnectionManager()
        # Fill the user to the cap.
        for _ in range(MAX_CONNECTIONS_PER_USER):
            ws = make_ws()
            assert connect(mgr, ws, user_id=1) is True

        assert len(mgr._active_connections[1]) == MAX_CONNECTIONS_PER_USER

        # The next (11th by default) connection is rejected & closed with 1013.
        overflow = make_ws()
        result = connect(mgr, overflow, user_id=1)

        assert result is False
        overflow.close.assert_awaited_once_with(
            code=1013, reason="Too many connections"
        )
        overflow.accept.assert_not_awaited()
        # Rejected socket must not be tracked.
        assert overflow not in mgr._active_connections[1]
        assert len(mgr._active_connections[1]) == MAX_CONNECTIONS_PER_USER

    def test_cap_is_per_user_not_global(self):
        mgr = ConnectionManager()
        for _ in range(MAX_CONNECTIONS_PER_USER):
            connect(mgr, make_ws(), user_id=1)

        # A different user is unaffected by user 1 hitting the cap.
        other = make_ws()
        assert connect(mgr, other, user_id=2) is True
        other.accept.assert_awaited_once()


# --------------------------------------------------------------------------- #
# disconnect()
# --------------------------------------------------------------------------- #
class TestDisconnect:
    def test_removes_socket(self):
        mgr = ConnectionManager()
        ws = make_ws()
        connect(mgr, ws, user_id=1)

        mgr.disconnect(ws, user_id=1)

        assert 1 not in mgr._active_connections

    def test_keeps_other_sockets_of_same_user(self):
        mgr = ConnectionManager()
        a, b = make_ws(), make_ws()
        connect(mgr, a, user_id=1)
        connect(mgr, b, user_id=1)

        mgr.disconnect(a, user_id=1)

        assert mgr._active_connections[1] == {b}

    def test_removes_from_admin_bucket(self):
        mgr = ConnectionManager()
        ws = make_ws()
        connect(mgr, ws, user_id=3, is_admin=True)

        mgr.disconnect(ws, user_id=3)

        assert ws not in mgr._admin_connections
        assert 3 not in mgr._active_connections

    def test_unknown_user_is_noop(self):
        mgr = ConnectionManager()
        # Should not raise.
        mgr.disconnect(make_ws(), user_id=999)

    def test_unknown_socket_known_user_is_noop(self):
        mgr = ConnectionManager()
        tracked = make_ws()
        connect(mgr, tracked, user_id=1)

        mgr.disconnect(make_ws(), user_id=1)  # different socket

        # The tracked socket is untouched.
        assert mgr._active_connections[1] == {tracked}


# --------------------------------------------------------------------------- #
# broadcast_to_user()
# --------------------------------------------------------------------------- #
class TestBroadcastToUser:
    def test_sends_to_all_sockets_of_user(self):
        mgr = ConnectionManager()
        a, b = make_ws(), make_ws()
        connect(mgr, a, user_id=1)
        connect(mgr, b, user_id=1)

        msg = {"type": "update", "x": 1}
        asyncio.run(mgr.broadcast_to_user(1, msg))

        a.send_json.assert_awaited_once_with(msg)
        b.send_json.assert_awaited_once_with(msg)

    def test_unknown_user_sends_nothing(self):
        mgr = ConnectionManager()
        ws = make_ws()
        connect(mgr, ws, user_id=1)

        asyncio.run(mgr.broadcast_to_user(999, {"a": 1}))

        ws.send_json.assert_not_awaited()

    def test_does_not_send_to_other_users(self):
        mgr = ConnectionManager()
        mine, theirs = make_ws(), make_ws()
        connect(mgr, mine, user_id=1)
        connect(mgr, theirs, user_id=2)

        asyncio.run(mgr.broadcast_to_user(1, {"a": 1}))

        mine.send_json.assert_awaited_once()
        theirs.send_json.assert_not_awaited()

    def test_failing_socket_is_cleaned_up(self):
        mgr = ConnectionManager()
        good, bad = make_ws(), make_ws()
        bad.send_json.side_effect = RuntimeError("connection reset")
        connect(mgr, good, user_id=1)
        connect(mgr, bad, user_id=1)

        # Must not propagate the exception.
        asyncio.run(mgr.broadcast_to_user(1, {"a": 1}))

        # Failing socket removed, healthy one retained.
        assert bad not in mgr._active_connections[1]
        assert good in mgr._active_connections[1]

    def test_all_sockets_failing_drops_user_entry(self):
        mgr = ConnectionManager()
        a, b = make_ws(), make_ws()
        a.send_json.side_effect = RuntimeError("boom")
        b.send_json.side_effect = RuntimeError("boom")
        connect(mgr, a, user_id=1)
        connect(mgr, b, user_id=1)

        asyncio.run(mgr.broadcast_to_user(1, {"a": 1}))

        assert 1 not in mgr._active_connections


# --------------------------------------------------------------------------- #
# broadcast_to_admin()
# --------------------------------------------------------------------------- #
class TestBroadcastToAdmin:
    def test_only_admins_receive(self):
        mgr = ConnectionManager()
        admin = make_ws()
        plain = make_ws()
        connect(mgr, admin, user_id=1, is_admin=True)
        connect(mgr, plain, user_id=2, is_admin=False)

        msg = {"type": "admin"}
        asyncio.run(mgr.broadcast_to_admin(msg))

        admin.send_json.assert_awaited_once_with(msg)
        plain.send_json.assert_not_awaited()

    def test_no_admins_sends_nothing(self):
        mgr = ConnectionManager()
        plain = make_ws()
        connect(mgr, plain, user_id=2)

        asyncio.run(mgr.broadcast_to_admin({"a": 1}))

        plain.send_json.assert_not_awaited()

    def test_failing_admin_socket_is_cleaned_up(self):
        mgr = ConnectionManager()
        admin = make_ws()
        admin.send_json.side_effect = RuntimeError("gone")
        connect(mgr, admin, user_id=5, is_admin=True)

        asyncio.run(mgr.broadcast_to_admin({"a": 1}))

        # Removed from both buckets via disconnect().
        assert admin not in mgr._admin_connections
        assert 5 not in mgr._active_connections


# --------------------------------------------------------------------------- #
# broadcast_to_all()
# --------------------------------------------------------------------------- #
class TestBroadcastToAll:
    def test_every_connection_receives(self):
        mgr = ConnectionManager()
        a, b, c = make_ws(), make_ws(), make_ws()
        connect(mgr, a, user_id=1)
        connect(mgr, b, user_id=1)
        connect(mgr, c, user_id=2)

        msg = {"type": "global"}
        asyncio.run(mgr.broadcast_to_all(msg))

        for ws in (a, b, c):
            ws.send_json.assert_awaited_once_with(msg)

    def test_empty_manager_is_noop(self):
        mgr = ConnectionManager()
        # Should not raise.
        asyncio.run(mgr.broadcast_to_all({"a": 1}))

    def test_failing_socket_cleaned_up_others_still_sent(self):
        mgr = ConnectionManager()
        good, bad, other = make_ws(), make_ws(), make_ws()
        bad.send_json.side_effect = RuntimeError("boom")
        connect(mgr, good, user_id=1)
        connect(mgr, bad, user_id=1)
        connect(mgr, other, user_id=2)

        asyncio.run(mgr.broadcast_to_all({"a": 1}))

        good.send_json.assert_awaited_once()
        other.send_json.assert_awaited_once()
        assert bad not in mgr._active_connections.get(1, set())
        assert good in mgr._active_connections[1]


# --------------------------------------------------------------------------- #
# broadcast_to_project()
# --------------------------------------------------------------------------- #
class TestBroadcastToProject:
    def test_owner_and_admins_receive_non_owners_do_not(self):
        mgr = ConnectionManager()
        owner = make_ws()
        admin = make_ws()
        stranger = make_ws()
        connect(mgr, owner, user_id=1)
        connect(mgr, admin, user_id=2, is_admin=True)
        connect(mgr, stranger, user_id=3)

        msg = {"type": "task", "project_id": 42}
        asyncio.run(mgr.broadcast_to_project(owner_id=1, message=msg))

        owner.send_json.assert_awaited_once_with(msg)
        admin.send_json.assert_awaited_once_with(msg)
        stranger.send_json.assert_not_awaited()

    def test_unresolved_owner_only_admins_receive(self):
        mgr = ConnectionManager()
        admin = make_ws()
        plain = make_ws()
        connect(mgr, admin, user_id=2, is_admin=True)
        connect(mgr, plain, user_id=3)

        # owner_id=None (e.g. project deleted): only admins get it.
        asyncio.run(mgr.broadcast_to_project(owner_id=None, message={"a": 1}))

        admin.send_json.assert_awaited_once()
        plain.send_json.assert_not_awaited()

    def test_owner_with_no_admins(self):
        mgr = ConnectionManager()
        owner = make_ws()
        connect(mgr, owner, user_id=1)

        asyncio.run(mgr.broadcast_to_project(owner_id=1, message={"a": 1}))

        owner.send_json.assert_awaited_once()

    def test_unknown_owner_and_no_admins_is_noop(self):
        mgr = ConnectionManager()
        plain = make_ws()
        connect(mgr, plain, user_id=3)

        asyncio.run(mgr.broadcast_to_project(owner_id=99, message={"a": 1}))

        plain.send_json.assert_not_awaited()

    def test_failing_owner_socket_cleaned_up(self):
        mgr = ConnectionManager()
        owner = make_ws()
        owner.send_json.side_effect = RuntimeError("boom")
        connect(mgr, owner, user_id=1)

        asyncio.run(mgr.broadcast_to_project(owner_id=1, message={"a": 1}))

        assert 1 not in mgr._active_connections

    def test_failing_admin_socket_cleaned_up(self):
        mgr = ConnectionManager()
        admin = make_ws()
        admin.send_json.side_effect = RuntimeError("boom")
        connect(mgr, admin, user_id=5, is_admin=True)

        asyncio.run(mgr.broadcast_to_project(owner_id=None, message={"a": 1}))

        assert admin not in mgr._admin_connections
        assert 5 not in mgr._active_connections

    def test_admin_owner_receives_message_once(self):
        mgr = ConnectionManager()
        # Same user is both the project owner and an admin.
        admin_owner = make_ws()
        connect(mgr, admin_owner, user_id=1, is_admin=True)

        asyncio.run(mgr.broadcast_to_project(owner_id=1, message={"a": 1}))

        # Deduplicated to a single send (the `sent` set guards the owner loop).
        assert admin_owner.send_json.await_count == 1


# --------------------------------------------------------------------------- #
# Module singleton
# --------------------------------------------------------------------------- #
class TestSingleton:
    def test_module_exposes_manager_singleton(self):
        assert isinstance(manager, ConnectionManager)

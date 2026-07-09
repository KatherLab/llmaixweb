# backend/src/websocket_manager.py
"""WebSocket connection manager for real-time task updates."""

import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Per-user cap on simultaneous WebSocket connections. Without it an
# authenticated user could open thousands of sockets and exhaust server
# file descriptors / memory. 10 is comfortably more than a single user with
# a few browser tabs would ever open. Excess connections are rejected with
# code 1013 ("Try Again Later") so the client can back off.
MAX_CONNECTIONS_PER_USER = 10


class ConnectionManager:
    """Manages WebSocket connections for broadcasting task updates."""

    def __init__(self):
        # Store active connections: {user_id: set of websockets}
        self._active_connections: Dict[int, Set[WebSocket]] = {}
        # Store all connections for admin broadcasts
        self._admin_connections: Set[WebSocket] = set()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        is_admin: bool = False,
        subprotocol: str | None = None,
    ):
        """Accept a new WebSocket connection.

        Rejects the connection with code 1013 if the user already holds
        ``MAX_CONNECTIONS_PER_USER`` open sockets, so one user can't exhaust
        server FDs/memory by opening unlimited connections.

        ``subprotocol`` is echoed back in the handshake when the client
        authenticated via the ``Sec-WebSocket-Protocol`` header (token-in-
        subprotocol); browsers require the server to confirm the negotiated
        subprotocol or they abort the connection.
        """
        existing = self._active_connections.get(user_id, set())
        if len(existing) >= MAX_CONNECTIONS_PER_USER:
            logger.warning(
                f"WebSocket rejected for user {user_id}: "
                f"{len(existing)} connections already open (cap "
                f"{MAX_CONNECTIONS_PER_USER})"
            )
            await websocket.close(code=1013, reason="Too many connections")
            return False

        await websocket.accept(subprotocol=subprotocol)

        if user_id not in self._active_connections:
            self._active_connections[user_id] = set()

        self._active_connections[user_id].add(websocket)

        if is_admin:
            self._admin_connections.add(websocket)

        logger.info(f"WebSocket connected for user {user_id}")
        return True

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self._active_connections:
            self._active_connections[user_id].discard(websocket)
            if not self._active_connections[user_id]:
                del self._active_connections[user_id]

        self._admin_connections.discard(websocket)
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def broadcast_to_user(self, user_id: int, message: dict):
        """Send a message to all connections for a specific user."""
        if user_id not in self._active_connections:
            return

        disconnected = set()
        for websocket in self._active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                disconnected.add(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws, user_id)

    async def broadcast_to_admin(self, message: dict):
        """Send a message to all admin connections."""
        disconnected = set()
        for websocket in self._admin_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to admin: {e}")
                disconnected.add(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            # Find user_id for this websocket
            for uid, sockets in self._active_connections.items():
                if ws in sockets:
                    self.disconnect(ws, uid)
                    break

    async def broadcast_to_all(self, message: dict):
        """Send a message to all connected clients.

        .. warning::
            This sends to *every* connected user regardless of project
            ownership, so it must only be used for messages that contain no
            user-specific data (e.g. global system broadcasts). Task/trial
            updates carry a ``project_id`` and must go through
            :meth:`broadcast_to_project`, which filters by ownership so a user
            can't observe another user's task progress.
        """
        disconnected = []

        for user_id, sockets in list(self._active_connections.items()):
            for websocket in sockets:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id}: {e}")
                    disconnected.append((websocket, user_id))

        # Clean up disconnected sockets
        for ws, uid in disconnected:
            self.disconnect(ws, uid)

    async def broadcast_to_project(self, owner_id: int | None, message: dict):
        """Send a project-scoped message to its owner and all admins.

        Task/trial update payloads include a ``project_id`` but the WebSocket
        layer previously broadcast them to *every* connected user, relying on
        the frontend to filter — a client that didn't filter could see other
        users' task progress. This filters server-side: the message is
        delivered only to the project owner's connections and to admin
        connections. Only admins with cross-user project access
        (``ADMIN_ALL_PROJECT_ACCESS``) join the admin bucket, so by default an
        admin sees just their own projects' updates. ``owner_id`` is resolved
        by the caller from the
        payload's ``project_id``; when it can't be resolved (e.g. project
        deleted), only admins receive the message.
        """
        disconnected = []

        # Admin connections always receive project updates.
        for websocket in list(self._admin_connections):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to admin: {e}")
                disconnected.append((websocket, None))

        # The owner's connections (if any) receive their own project's updates.
        if owner_id is not None and owner_id in self._active_connections:
            for websocket in list(self._active_connections[owner_id]):
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {owner_id}: {e}")
                    disconnected.append((websocket, owner_id))

        for ws, uid in disconnected:
            if uid is not None:
                self.disconnect(ws, uid)
            else:
                # Admin socket: find its user id for cleanup.
                for cand_uid, sockets in self._active_connections.items():
                    if ws in sockets:
                        self.disconnect(ws, cand_uid)
                        break
                else:
                    self._admin_connections.discard(ws)


# Global singleton instance
manager = ConnectionManager()

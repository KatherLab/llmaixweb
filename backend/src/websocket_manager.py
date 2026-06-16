# backend/src/websocket_manager.py
"""WebSocket connection manager for real-time task updates."""

import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for broadcasting task updates."""

    def __init__(self):
        # Store active connections: {user_id: set of websockets}
        self._active_connections: Dict[int, Set[WebSocket]] = {}
        # Store all connections for admin broadcasts
        self._admin_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, user_id: int, is_admin: bool = False):
        """Accept a new WebSocket connection."""
        await websocket.accept()

        if user_id not in self._active_connections:
            self._active_connections[user_id] = set()

        self._active_connections[user_id].add(websocket)

        if is_admin:
            self._admin_connections.add(websocket)

        logger.info(f"WebSocket connected for user {user_id}")

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
        """Send a message to all connected clients."""
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


# Global singleton instance
manager = ConnectionManager()

"""WebSocket manager for real-time attendance updates."""

import json
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections grouped by session_id."""

    def __init__(self):
        # Maps session_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        """Accept and register a WebSocket connection for a session."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: int):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast_to_session(self, session_id: int, data: dict):
        """Send data to all WebSocket connections watching a session."""
        if session_id not in self.active_connections:
            return
        dead_connections = set()
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(data)
            except Exception:
                dead_connections.add(connection)
        # Clean up dead connections
        for conn in dead_connections:
            self.active_connections[session_id].discard(conn)


# Global instance
manager = ConnectionManager()

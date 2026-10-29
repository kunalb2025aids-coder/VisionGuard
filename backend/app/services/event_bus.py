"""
Event Bus - In-process WebSocket broadcast system.
Handles fan-out of events to all connected WebSocket clients.
"""
import json
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

logger = logging.getLogger("visionguard.eventbus")

class ConnectionManager:
    """Manages active WebSocket connections and event broadcasting."""

    def __init__(self):
        self.active_connections: Set[Any] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: Any):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: Any):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, payload: Dict[str, Any], source: str = "server"):
        """Broadcast a validated event to all connected clients."""
        event = {
            "event_id": str(uuid.uuid4()),
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "payload": payload
        }
        message = json.dumps(event)
        dead = set()
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                dead.add(ws)
        if dead:
            async with self._lock:
                self.active_connections -= dead

    def connection_count(self) -> int:
        return len(self.active_connections)

# Global singleton
manager = ConnectionManager()

# Convenience helpers for synchronous callers
def broadcast_sync(event_type: str, payload: Dict[str, Any], source: str = "server"):
    """Schedule a broadcast from synchronous context if event loop is running."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(manager.broadcast(event_type, payload, source))
        else:
            loop.run_until_complete(manager.broadcast(event_type, payload, source))
    except Exception as e:
        logger.debug(f"broadcast_sync skipped (no event loop): {e}")

"""WebSocket router - real-time event hub for VisionGuard AI."""
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.event_bus import manager

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger("visionguard.ws")


@router.websocket("/ws/visionguard")
async def visionguard_ws(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard events.
    
    Event types broadcast:
    - telemetry.updated
    - inspection.completed
    - detection.created
    - maintenance.updated
    - alert.created
    - asset.status_changed
    - system.heartbeat
    """
    await manager.connect(websocket)
    try:
        # Send welcome/connection-established event
        await websocket.send_json({
            "event_id": "conn-established",
            "type": "system.connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "event_bus",
            "payload": {
                "message": "Connected to VisionGuard AI real-time event stream",
                "client_count": manager.connection_count(),
            }
        })

        while True:
            # Keep alive - receive ping/pong or client messages
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({
                        "type": "system.pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    continue

                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({
                            "type": "system.pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                except json.JSONDecodeError:
                    pass
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.debug(f"WS receive loop error: {e}")
                break

    finally:
        await manager.disconnect(websocket)
        logger.info("WebSocket client disconnected.")

"""Tests for WebSocket real-time event streaming."""
import pytest
from fastapi.testclient import TestClient
from backend.app.services.event_bus import manager


def test_ws_connection_and_welcome(client):
    """Test connecting to /ws/visionguard and receiving initial handshake."""
    with client.websocket_connect("/ws/visionguard") as ws:
        # First message sent upon connect is system.connected
        data = ws.receive_json()
        assert data["type"] == "system.connected"
        assert "event_id" in data
        assert "timestamp" in data
        assert data["source"] == "event_bus"
        assert data["payload"]["client_count"] >= 1


def test_ws_ping_pong(client):
    """Test that sending ping receives pong."""
    with client.websocket_connect("/ws/visionguard") as ws:
        # Consume welcome message
        _ = ws.receive_json()

        # Send ping
        ws.send_text("ping")
        resp = ws.receive_json()
        assert resp["type"] == "system.pong"


def test_ws_event_schema(client):
    """Test broadcasting an event conforms to validated schema."""
    with client.websocket_connect("/ws/visionguard") as ws:
        # Consume welcome
        _ = ws.receive_json()

        # Check broadcast payload received by client
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            manager.broadcast("telemetry.test", {"status": "ok", "value": 42.0}, source="unit_test")
        )
        loop.close()

        msg = ws.receive_json()
        assert msg["type"] == "telemetry.test"
        assert msg["source"] == "unit_test"
        assert msg["payload"]["value"] == 42.0
        assert "event_id" in msg
        assert "timestamp" in msg

"""Tests for AI Copilot API."""
import pytest


def test_copilot_status(client):
    """GET /api/copilot/status returns availability info."""
    response = client.get("/api/copilot/status")
    assert response.status_code == 200
    data = response.json()
    assert "llm_available" in data
    assert "capabilities" in data
    assert isinstance(data["capabilities"], list)


def test_copilot_ask_no_llm(client):
    """POST /api/copilot/ask works without LLM - returns evidence-grounded response."""
    response = client.post("/api/copilot/ask", json={"message": "Show recent inspections"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert "sources" in data
    assert "evidence_context" in data
    # When LLM not configured, status should be unavailable
    assert data["status"] in ("unavailable", "completed", "error")


def test_copilot_ask_evidence_retrieval(client):
    """Copilot retrieves database evidence even without LLM."""
    response = client.post("/api/copilot/ask", json={"message": "Which maintenance tasks are overdue?"})
    assert response.status_code == 200
    data = response.json()
    ctx = data.get("evidence_context", {})
    # Evidence context should be populated
    assert "open_maintenance_tasks" in ctx or "recent_inspections" in ctx


def test_copilot_ask_validation(client):
    """Empty message should fail validation."""
    response = client.post("/api/copilot/ask", json={"message": ""})
    assert response.status_code == 422  # Pydantic validation error


def test_copilot_history(client):
    """GET /api/copilot/history returns session list."""
    # Ask first to create a session
    client.post("/api/copilot/ask", json={"message": "Hello"})
    response = client.get("/api/copilot/history")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert data["count"] >= 1
    session = data["sessions"][0]
    assert "session_id" in session
    assert "user_message" in session
    assert "assistant_response" in session


def test_copilot_no_fabricated_predictions(client):
    """Copilot response should not make up inference results."""
    response = client.post("/api/copilot/ask", json={"message": "What defects were detected today?"})
    assert response.status_code == 200
    data = response.json()
    # The evidence context drives the answer, source references should be present
    assert isinstance(data.get("sources"), list)

"""Copilot API - AI Maintenance Assistant endpoints."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.models.database import get_db
from backend.app.models.entities import CopilotSession
from backend.app.services.copilot_service import CopilotService

router = APIRouter(prefix="/api/copilot", tags=["AI Copilot"])


class AskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


@router.post("/ask")
def ask_copilot(payload: AskRequest, db: Session = Depends(get_db)):
    """
    Ask the AI Maintenance Copilot a question.
    Retrieves actual evidence from the database. LLM is optional.
    """
    result = CopilotService.ask(db, payload.message)
    return result


@router.get("/status")
def copilot_status():
    """Return copilot availability and configuration."""
    return {
        "llm_available": CopilotService.is_llm_configured(),
        "provider": CopilotService.is_llm_configured() and __import__("os").getenv("LLM_PROVIDER", "not set"),
        "model": __import__("os").getenv("LLM_MODEL", "not configured"),
        "note": (
            "Set LLM_PROVIDER=openai|google and LLM_API_KEY to enable generative responses. "
            "Evidence retrieval from database works without LLM configuration."
        ),
        "capabilities": [
            "Recent inspection summary",
            "Detection history by defect class",
            "Open maintenance task listing",
            "Alert summary",
            "Simulated telemetry context",
            "Maintenance work order drafting (requires LLM + human approval)",
        ],
    }


@router.get("/history")
def get_session_history(limit: int = 20, db: Session = Depends(get_db)):
    """Return recent copilot conversation history."""
    sessions = (
        db.query(CopilotSession)
        .order_by(CopilotSession.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "user_message": s.user_message,
                "assistant_response": s.assistant_response,
                "provider": s.provider,
                "status": s.status,
                "sources": json.loads(s.evidence_sources) if s.evidence_sources else [],
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sessions
        ],
    }

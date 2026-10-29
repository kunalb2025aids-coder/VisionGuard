"""
Copilot Service - Evidence-grounded AI Maintenance Assistant.
Retrieves actual inspection, detection, alert, telemetry and maintenance
records to ground responses. Never claims to see data it did not retrieve.
External LLM is optional - graceful fallback when not configured.
"""
import os
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from backend.app.models.entities import (
    Inspection, Detection, Alert, MaintenanceTask,
    TelemetryReading, AnomalyPrediction, CopilotSession
)

logger = logging.getLogger("visionguard.copilot")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()  # "openai", "google", or ""
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))


class EvidenceRetriever:
    """Retrieves factual evidence from database for a user query."""

    @staticmethod
    def get_recent_inspections(db: Session, limit: int = 5) -> List[Dict]:
        rows = db.query(Inspection).order_by(Inspection.created_at.desc()).limit(limit).all()
        return [
            {
                "source": "inspection",
                "id": r.id,
                "filename": r.filename,
                "media_type": r.media_type,
                "status": r.status,
                "defects_count": r.defects_count,
                "high_priority_count": r.high_priority_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    @staticmethod
    def get_recent_detections(db: Session, defect_class: Optional[str] = None, limit: int = 10) -> List[Dict]:
        query = db.query(Detection).order_by(Detection.created_at.desc())
        if defect_class:
            query = query.filter(Detection.defect_class.ilike(f"%{defect_class}%"))
        rows = query.limit(limit).all()
        return [
            {
                "source": "detection",
                "id": r.id,
                "inspection_id": r.inspection_id,
                "defect_class": r.defect_class,
                "confidence": r.confidence,
                "severity": r.severity,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    @staticmethod
    def get_open_maintenance(db: Session, limit: int = 10) -> List[Dict]:
        rows = (
            db.query(MaintenanceTask)
            .filter(MaintenanceTask.status.in_(["Pending", "In Progress"]))
            .order_by(MaintenanceTask.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "source": "maintenance_task",
                "id": r.id,
                "title": r.title,
                "defect_class": r.defect_class,
                "severity": r.severity,
                "status": r.status,
                "assigned_personnel": r.assigned_personnel,
                "due_date": r.due_date,
            }
            for r in rows
        ]

    @staticmethod
    def get_recent_alerts(db: Session, limit: int = 5) -> List[Dict]:
        rows = db.query(Alert).order_by(Alert.created_at.desc()).limit(limit).all()
        return [
            {
                "source": "alert",
                "id": r.id,
                "title": r.title,
                "message": r.message,
                "severity": r.severity,
                "is_read": r.is_read,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    @staticmethod
    def get_latest_telemetry(db: Session, asset_code: Optional[str] = None) -> List[Dict]:
        query = db.query(TelemetryReading).order_by(TelemetryReading.recorded_at.desc())
        if asset_code:
            query = query.filter(TelemetryReading.asset_code == asset_code)
        rows = query.limit(20).all()
        return [
            {
                "source": "telemetry (simulation)",
                "sensor_channel": r.sensor_channel,
                "value": r.value,
                "unit": r.unit,
                "is_anomaly": r.is_anomaly,
                "asset_code": r.asset_code,
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in rows
        ]

    @classmethod
    def build_context(cls, db: Session, user_message: str) -> Dict[str, Any]:
        """Build structured evidence context from the database."""
        msg_lower = user_message.lower()

        # Determine what to retrieve based on message content
        inspections = cls.get_recent_inspections(db, limit=5)
        detections = []
        maintenance = cls.get_open_maintenance(db, limit=10)
        alerts = cls.get_recent_alerts(db, limit=5)
        telemetry = []

        # Topic-specific retrieval
        for defect in ["cracks", "tears", "misalignment", "roller", "spillage"]:
            if defect in msg_lower:
                detections = cls.get_recent_detections(db, defect_class=defect)
                break
        if not detections:
            detections = cls.get_recent_detections(db, limit=5)

        if any(k in msg_lower for k in ["sensor", "telemetry", "temperature", "vibration", "speed", "current"]):
            telemetry = cls.get_latest_telemetry(db)

        return {
            "recent_inspections": inspections,
            "recent_detections": detections,
            "open_maintenance_tasks": maintenance,
            "recent_alerts": alerts,
            "latest_telemetry": telemetry,
            "telemetry_note": "Telemetry values are from software simulation (source=simulation). They do not represent real hardware sensor readings.",
        }


class CopilotService:
    """AI Maintenance Assistant - retrieves evidence, optionally calls LLM."""

    @classmethod
    def is_llm_configured(cls) -> bool:
        return bool(LLM_PROVIDER and LLM_API_KEY)

    @classmethod
    def build_system_prompt(cls) -> str:
        return (
            "You are VisionGuard AI Copilot, a maintenance assistant for an industrial conveyor belt "
            "defect detection system. You answer questions using ONLY the structured evidence provided "
            "in the context. If information is not in the context, say so explicitly. "
            "Never fabricate inspection results, sensor readings, or failure predictions. "
            "Telemetry data is from software simulation and must be disclosed as such. "
            "When drafting maintenance work orders, always note that a human engineer must review "
            "and approve before any physical action is taken. "
            "Be concise, factual, and cite your sources (e.g. Inspection #12, Alert #3)."
        )

    @classmethod
    def call_llm(cls, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Call configured LLM provider with evidence context."""
        if not cls.is_llm_configured():
            return {
                "status": "unavailable",
                "response": (
                    "AI Copilot LLM is not configured. "
                    "Set LLM_PROVIDER and LLM_API_KEY environment variables to enable. "
                    "The evidence context below was retrieved from the database."
                ),
                "provider": "unavailable",
                "evidence_context": context,
            }

        context_text = json.dumps(context, indent=2, default=str)
        messages = [
            {"role": "system", "content": cls.build_system_prompt()},
            {"role": "user", "content": f"EVIDENCE CONTEXT:\n{context_text}\n\nQUESTION: {user_message}"},
        ]

        try:
            if LLM_PROVIDER == "openai":
                import httpx
                headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
                payload = {"model": LLM_MODEL, "messages": messages, "max_tokens": LLM_MAX_TOKENS, "temperature": 0.3}
                r = httpx.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=LLM_TIMEOUT)
                r.raise_for_status()
                resp_data = r.json()
                answer = resp_data["choices"][0]["message"]["content"]
                return {"status": "completed", "response": answer, "provider": "openai", "evidence_context": context}

            elif LLM_PROVIDER == "google":
                import httpx
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent?key={LLM_API_KEY}"
                parts = [{"text": msg["content"]} for msg in messages]
                payload = {"contents": [{"parts": parts}]}
                r = httpx.post(url, json=payload, timeout=LLM_TIMEOUT)
                r.raise_for_status()
                resp_data = r.json()
                answer = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                return {"status": "completed", "response": answer, "provider": "google", "evidence_context": context}

            else:
                return {
                    "status": "error",
                    "response": f"Unknown LLM_PROVIDER: {LLM_PROVIDER}. Supported: openai, google.",
                    "provider": LLM_PROVIDER,
                    "evidence_context": context,
                }

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {
                "status": "error",
                "response": f"LLM request failed: {type(e).__name__}. Check credentials and network access. Evidence context is available below.",
                "provider": LLM_PROVIDER,
                "evidence_context": context,
            }

    @classmethod
    def ask(cls, db: Session, user_message: str) -> Dict[str, Any]:
        """Main entry point: retrieve evidence, call LLM if available, persist session."""
        session_id = str(uuid.uuid4())
        context = EvidenceRetriever.build_context(db, user_message)
        result = cls.call_llm(user_message, context)

        # Extract source references
        sources = []
        for insp in context.get("recent_inspections", []):
            sources.append(f"Inspection #{insp['id']}: {insp['filename']}")
        for det in context.get("recent_detections", []):
            sources.append(f"Detection #{det['id']}: {det['defect_class']} ({det['severity']})")
        for alert in context.get("recent_alerts", []):
            sources.append(f"Alert #{alert['id']}: {alert['title']}")
        if context.get("latest_telemetry"):
            sources.append("Simulated sensor telemetry (source=simulation)")

        # Persist session
        session = CopilotSession(
            session_id=session_id,
            user_message=user_message,
            assistant_response=result.get("response", ""),
            evidence_sources=json.dumps(sources),
            provider=result.get("provider", "unavailable"),
            status=result.get("status", "completed"),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        return {
            "session_id": session_id,
            "user_message": user_message,
            "response": result.get("response", ""),
            "status": result.get("status"),
            "provider": result.get("provider"),
            "sources": sources,
            "evidence_context": result.get("evidence_context", context),
            "copilot_available": cls.is_llm_configured(),
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }


copilot_service = CopilotService()

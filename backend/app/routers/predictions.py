"""Predictions API - anomaly indicators and model status."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.models.database import get_db
from backend.app.models.entities import AnomalyPrediction
from backend.app.services.prediction_service import PredictionService, SKLEARN_AVAILABLE

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.get("/status")
def prediction_status():
    """Return model readiness and metadata."""
    return {
        "service": "VisionGuard AI Predictive Maintenance",
        "disclaimer": (
            "This service provides anomaly INDICATORS, not validated equipment failure predictions. "
            "Threshold breaches and ML anomaly scores require engineer review before action. "
            "Do not conflate with YOLO visual defect detection results."
        ),
        **PredictionService.status(),
    }


@router.get("/anomalies")
def list_anomalies(
    asset_code: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List persisted anomaly indicators."""
    query = db.query(AnomalyPrediction)
    if asset_code:
        query = query.filter(AnomalyPrediction.asset_code == asset_code)
    if status_filter:
        query = query.filter(AnomalyPrediction.status == status_filter)
    rows = query.order_by(AnomalyPrediction.created_at.desc()).limit(limit).all()

    return {
        "count": len(rows),
        "anomalies": [
            {
                "id": r.id,
                "asset_code": r.asset_code,
                "prediction_type": r.prediction_type,
                "sensor_channel": r.sensor_channel,
                "actual_value": r.actual_value,
                "threshold_value": r.threshold_value,
                "anomaly_score": r.anomaly_score,
                "severity": r.severity,
                "status": r.status,
                "model_version": r.model_version,
                "source": r.source,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "evidence": r.evidence,
            }
            for r in rows
        ],
        "disclaimer": "Anomaly indicators from threshold rules or IsolationForest. Not validated failure predictions.",
    }


@router.put("/anomalies/{anomaly_id}/acknowledge")
def acknowledge_anomaly(anomaly_id: int, db: Session = Depends(get_db)):
    """Acknowledge an anomaly indicator (engineer review)."""
    pred = db.query(AnomalyPrediction).filter(AnomalyPrediction.id == anomaly_id).first()
    if not pred:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Anomaly indicator {anomaly_id} not found")
    pred.status = "acknowledged"
    db.commit()
    return {"id": pred.id, "status": pred.status, "message": "Anomaly acknowledged by engineer."}

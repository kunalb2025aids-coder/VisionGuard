from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.models.database import get_db
from backend.app.models.entities import Alert
from backend.app.schemas.schemas import AlertSchema

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertSchema])
def list_alerts(
    unread_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if unread_only:
        query = query.filter(Alert.is_read == False)
    alerts = query.order_by(Alert.created_at.desc()).limit(50).all()
    return [AlertSchema.model_validate(a) for a in alerts]

@router.put("/{id}/read", response_model=AlertSchema)
def mark_alert_read(id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == id).first()
    if alert:
        alert.is_read = True
        db.commit()
        db.refresh(alert)
    return AlertSchema.model_validate(alert)

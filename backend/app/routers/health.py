from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.models.database import get_db
from backend.app.services.yolo_service import yolo_service
from backend.app.schemas.schemas import HealthResponseSchema

router = APIRouter(prefix="/api", tags=["Health"])

@router.get("/health", response_model=HealthResponseSchema)
def health_check(db: Session = Depends(get_db)):
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # Check and dynamically load model if weights exist
    model_loaded = yolo_service.ensure_loaded()

    return HealthResponseSchema(
        status="healthy" if db_ok else "unhealthy",
        model_loaded=model_loaded,
        model_path=yolo_service.model_path,
        database_connected=db_ok,
        timestamp=datetime.utcnow()
    )

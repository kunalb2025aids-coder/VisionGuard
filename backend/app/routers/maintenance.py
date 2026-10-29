from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.models.database import get_db
from backend.app.models.entities import MaintenanceTask
from backend.app.schemas.schemas import (
    MaintenanceTaskSchema,
    MaintenanceTaskCreateSchema,
    MaintenanceTaskUpdateSchema
)

router = APIRouter(prefix="/api/maintenance", tags=["Maintenance"])

@router.get("", response_model=List[MaintenanceTaskSchema])
def list_maintenance_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity_filter: Optional[str] = Query(None, alias="severity"),
    db: Session = Depends(get_db)
):
    query = db.query(MaintenanceTask)
    if status_filter:
        query = query.filter(MaintenanceTask.status == status_filter)
    if severity_filter:
        query = query.filter(MaintenanceTask.severity == severity_filter)
    
    tasks = query.order_by(MaintenanceTask.updated_at.desc()).all()
    return [MaintenanceTaskSchema.model_validate(t) for t in tasks]

@router.post("", response_model=MaintenanceTaskSchema, status_code=status.HTTP_201_CREATED)
def create_maintenance_task(
    payload: MaintenanceTaskCreateSchema,
    db: Session = Depends(get_db)
):
    task = MaintenanceTask(
        inspection_id=payload.inspection_id,
        detection_id=payload.detection_id,
        title=payload.title,
        defect_class=payload.defect_class,
        severity=payload.severity,
        assigned_personnel=payload.assigned_personnel or "Unassigned",
        due_date=payload.due_date,
        status=payload.status,
        notes=payload.notes or "",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        from backend.app.services.event_bus import broadcast_sync
        broadcast_sync("maintenance.updated", {
            "id": task.id,
            "title": task.title,
            "severity": task.severity,
            "status": task.status,
            "action": "created"
        }, source="maintenance_api")
    except Exception:
        pass

    return MaintenanceTaskSchema.model_validate(task)

@router.put("/{id}", response_model=MaintenanceTaskSchema)
def update_maintenance_task(
    id: int,
    payload: MaintenanceTaskUpdateSchema,
    db: Session = Depends(get_db)
):
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Maintenance task with ID {id} not found")

    if payload.title is not None:
        task.title = payload.title
    if payload.severity is not None:
        task.severity = payload.severity
    if payload.assigned_personnel is not None:
        task.assigned_personnel = payload.assigned_personnel
    if payload.due_date is not None:
        task.due_date = payload.due_date
    if payload.status is not None:
        task.status = payload.status
    if payload.notes is not None:
        task.notes = payload.notes

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    try:
        from backend.app.services.event_bus import broadcast_sync
        broadcast_sync("maintenance.updated", {
            "id": task.id,
            "title": task.title,
            "severity": task.severity,
            "status": task.status,
            "action": "updated"
        }, source="maintenance_api")
    except Exception:
        pass

    return MaintenanceTaskSchema.model_validate(task)

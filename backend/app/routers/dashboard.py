from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.database import get_db
from backend.app.models.entities import Inspection, Detection, MaintenanceTask
from backend.app.schemas.schemas import DashboardSummarySchema, InspectionSchema

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummarySchema)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_inspections = db.query(func.count(Inspection.id)).scalar() or 0
    total_defects = db.query(func.count(Detection.id)).scalar() or 0
    high_priority_defects = db.query(func.count(Detection.id)).filter(
        Detection.severity.in_(["High", "Critical"])
    ).scalar() or 0

    completed_maintenance = db.query(func.count(MaintenanceTask.id)).filter(
        MaintenanceTask.status == "Completed"
    ).scalar() or 0

    pending_maintenance = db.query(func.count(MaintenanceTask.id)).filter(
        MaintenanceTask.status != "Completed"
    ).scalar() or 0

    # Defects by category
    category_counts = db.query(
        Detection.defect_class, func.count(Detection.id)
    ).group_by(Detection.defect_class).all()
    
    # Initialize all default classes with 0
    defects_by_category = {
        "Cracks": 0,
        "Tears": 0,
        "Misalignment": 0,
        "Roller faults": 0,
        "Material spillage": 0
    }
    for cat, count in category_counts:
        defects_by_category[cat] = count

    # Defects by severity
    severity_counts = db.query(
        Detection.severity, func.count(Detection.id)
    ).group_by(Detection.severity).all()

    defects_by_severity = {
        "Low": 0,
        "Medium": 0,
        "High": 0,
        "Critical": 0
    }
    for sev, count in severity_counts:
        if sev in defects_by_severity:
            defects_by_severity[sev] = count

    # Recent inspection history (last 10)
    recent_inspections_db = db.query(Inspection).order_by(Inspection.created_at.desc()).limit(10).all()

    # Simple trend calculation (group by date)
    trend_data = db.query(
        func.date(Inspection.created_at).label("date"),
        func.count(Inspection.id).label("inspections"),
        func.sum(Inspection.defects_count).label("defects")
    ).group_by(func.date(Inspection.created_at)).order_by("date").limit(7).all()

    inspection_trends = [
        {
            "date": str(row.date),
            "inspections": row.inspections or 0,
            "defects": row.defects or 0
        }
        for row in trend_data
    ]

    return DashboardSummarySchema(
        total_inspections=total_inspections,
        total_defects=total_defects,
        high_priority_defects=high_priority_defects,
        completed_maintenance=completed_maintenance,
        pending_maintenance=pending_maintenance,
        defects_by_category=defects_by_category,
        defects_by_severity=defects_by_severity,
        inspection_trends=inspection_trends,
        recent_inspections=[InspectionSchema.model_validate(i) for i in recent_inspections_db]
    )

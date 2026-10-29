from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from backend.app.models.database import get_db
from backend.app.models.entities import Inspection, Detection, MaintenanceTask
from backend.app.services.report_service import ReportService
from backend.app.schemas.schemas import InspectionSchema

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/inspections")
def get_reports_inspections(db: Session = Depends(get_db)):
    inspections = db.query(Inspection).order_by(Inspection.created_at.desc()).all()
    total = len(inspections)
    total_defects = sum(i.defects_count for i in inspections)
    high_priority = sum(i.high_priority_count for i in inspections)
    avg_processing_time = (
        sum(i.processing_time_ms for i in inspections) / total if total > 0 else 0.0
    )

    return {
        "summary": {
            "total_inspections": total,
            "total_defects_found": total_defects,
            "high_priority_defects": high_priority,
            "avg_processing_time_ms": round(avg_processing_time, 2)
        },
        "inspections": [InspectionSchema.model_validate(i) for i in inspections]
    }

@router.get("/export")
def export_reports_csv(type: str = "full", db: Session = Depends(get_db)):
    if type == "inspections":
        csv_content = ReportService.generate_inspections_report_csv(db)
        filename = "visionguard_inspections_summary.csv"
    else:
        csv_content = ReportService.generate_full_report_csv(db)
        filename = "visionguard_detections_full_report.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

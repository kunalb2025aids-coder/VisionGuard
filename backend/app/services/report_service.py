import csv
import io
from typing import List
from sqlalchemy.orm import Session
from backend.app.models.entities import Inspection, Detection, MaintenanceTask

class ReportService:
    @staticmethod
    def generate_inspections_report_csv(db: Session) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write CSV Header
        writer.writerow([
            "Inspection ID",
            "Filename",
            "Media Type",
            "Status",
            "Defects Count",
            "High Priority Count",
            "Processing Time (ms)",
            "Inspection Date",
            "Original Path",
            "Result Path"
        ])

        inspections = db.query(Inspection).order_by(Inspection.created_at.desc()).all()
        for i in inspections:
            writer.writerow([
                i.id,
                i.filename,
                i.media_type,
                i.status,
                i.defects_count,
                i.high_priority_count,
                i.processing_time_ms,
                i.created_at.strftime("%Y-%m-%d %H:%M:%S") if i.created_at else "",
                i.original_path,
                i.result_path or ""
            ])

        return output.getvalue()

    @staticmethod
    def generate_full_report_csv(db: Session) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write Detailed Detections CSV Header
        writer.writerow([
            "Inspection ID",
            "Filename",
            "Media Type",
            "Inspection Date",
            "Detection ID",
            "Defect Class",
            "Confidence Score",
            "Severity (Preliminary)",
            "Bounding Box [x1,y1,x2,y2]",
            "Frame Number"
        ])

        detections = db.query(Detection).join(Inspection).order_by(Inspection.created_at.desc()).all()
        for d in detections:
            writer.writerow([
                d.inspection.id,
                d.inspection.filename,
                d.inspection.media_type,
                d.inspection.created_at.strftime("%Y-%m-%d %H:%M:%S") if d.inspection.created_at else "",
                d.id,
                d.defect_class,
                d.confidence,
                d.severity,
                d.bbox or "",
                d.frame_number or "N/A"
            ])

        return output.getvalue()

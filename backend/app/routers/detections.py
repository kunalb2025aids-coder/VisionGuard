import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.models.database import get_db
from backend.app.models.entities import Inspection, Detection, MaintenanceTask
from backend.app.services.yolo_service import yolo_service
from backend.app.services.alert_service import AlertService
from backend.app.schemas.schemas import InspectionSchema

router = APIRouter(prefix="/api/detections", tags=["Detections"])

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

def sanitize_filename(filename: str) -> str:
    # Protect against unsafe filenames / path traversal
    base_name = os.path.basename(filename)
    safe_name = "".join(c for c in base_name if c.isalnum() or c in "._-")
    return f"{uuid.uuid4().hex[:8]}_{safe_name}"

@router.post("/image", response_model=InspectionSchema, status_code=status.HTTP_201_CREATED)
async def upload_and_detect_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed image formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Check model readiness
    if not yolo_service.is_loaded:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ModelWeightsMissing",
                "message": yolo_service.error_message,
                "instructions": "Place custom trained YOLO11 model weights at 'models/best.pt' or run 'python train_yolo.py'."
            }
        )

    safe_name = sanitize_filename(file.filename)
    upload_path = os.path.join("uploads", safe_name)
    result_filename = f"annotated_{safe_name}"
    result_path = os.path.join("results", result_filename)

    os.makedirs("uploads", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    # Save uploaded file
    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    try:
        # Run inference
        prediction = yolo_service.predict_image(upload_path, result_path)
    except FileNotFoundError as fnf_err:
        raise HTTPException(status_code=400, detail=str(fnf_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing error: {str(e)}")

    detections_data = prediction["detections"]
    high_priority_count = sum(1 for d in detections_data if d["severity"] in ["High", "Critical"])

    # Create Inspection record in DB
    inspection = Inspection(
        filename=file.filename,
        media_type="image",
        original_path=upload_path,
        result_path=result_path,
        status="completed" if detections_data else "no_defects",
        defects_count=len(detections_data),
        high_priority_count=high_priority_count,
        processing_time_ms=prediction["processing_time_ms"],
        created_at=datetime.utcnow()
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    # Add Detection records
    for det in detections_data:
        detection_rec = Detection(
            inspection_id=inspection.id,
            defect_class=det["defect_class"],
            confidence=det["confidence"],
            severity=det["severity"],
            bbox=det["bbox"],
            frame_number=det["frame_number"]
        )
        db.add(detection_rec)
        db.commit()
        db.refresh(detection_rec)

        # Auto-create maintenance task for High or Critical defects
        if det["severity"] in ["High", "Critical"]:
            task = MaintenanceTask(
                inspection_id=inspection.id,
                detection_id=detection_rec.id,
                title=f"Repair {det['defect_class']} on conveyor belt",
                defect_class=det["defect_class"],
                severity=det["severity"],
                assigned_personnel="Unassigned",
                due_date=datetime.utcnow().strftime("%Y-%m-%d"),
                status="Pending",
                notes=f"Auto-generated maintenance task for preliminary {det['severity']} defect detected with {det['confidence']*100:.1f}% confidence."
            )
            db.add(task)
            db.commit()

    # Trigger alert if high priority defects exist
    if high_priority_count > 0:
        AlertService.create_alert(
            db=db,
            inspection_id=inspection.id,
            title=f"Critical Defect Alert: {file.filename}",
            message=f"Detected {high_priority_count} high/critical priority conveyor belt defects during inspection.",
            severity="Critical" if any(d["severity"] == "Critical" for d in detections_data) else "High"
        )

    db.refresh(inspection)
    return InspectionSchema.model_validate(inspection)

@router.post("/video", response_model=InspectionSchema, status_code=status.HTTP_201_CREATED)
async def upload_and_detect_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video extension '{ext}'. Allowed video formats: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )

    if not yolo_service.is_loaded:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ModelWeightsMissing",
                "message": yolo_service.error_message,
                "instructions": "Place custom trained YOLO11 model weights at 'models/best.pt' or run 'python train_yolo.py'."
            }
        )

    safe_name = sanitize_filename(file.filename)
    upload_path = os.path.join("uploads", safe_name)
    result_filename = f"annotated_{os.path.splitext(safe_name)[0]}.mp4"
    result_path = os.path.join("results", result_filename)

    os.makedirs("uploads", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    try:
        prediction = yolo_service.predict_video(upload_path, result_path)
    except FileNotFoundError as fnf_err:
        raise HTTPException(status_code=400, detail=str(fnf_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video processing error: {str(e)}")

    detections_data = prediction["detections"]
    high_priority_count = sum(1 for d in detections_data if d["severity"] in ["High", "Critical"])

    inspection = Inspection(
        filename=file.filename,
        media_type="video",
        original_path=upload_path,
        result_path=result_path,
        status="completed" if detections_data else "no_defects",
        defects_count=len(detections_data),
        high_priority_count=high_priority_count,
        processing_time_ms=prediction["processing_time_ms"],
        created_at=datetime.utcnow()
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    # Record first 50 detections to avoid DB flood for long videos
    for det in detections_data[:50]:
        detection_rec = Detection(
            inspection_id=inspection.id,
            defect_class=det["defect_class"],
            confidence=det["confidence"],
            severity=det["severity"],
            bbox=det["bbox"],
            frame_number=det["frame_number"]
        )
        db.add(detection_rec)

    db.commit()

    if high_priority_count > 0:
        AlertService.create_alert(
            db=db,
            inspection_id=inspection.id,
            title=f"Video Defect Alert: {file.filename}",
            message=f"Video analysis identified {len(detections_data)} defect occurrences ({high_priority_count} high priority).",
            severity="High"
        )

    db.refresh(inspection)
    return InspectionSchema.model_validate(inspection)

@router.get("", response_model=List[InspectionSchema])
def list_detections(
    skip: int = 0,
    limit: int = 50,
    media_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Inspection)
    if media_type:
        query = query.filter(Inspection.media_type == media_type)
    inspections = query.order_by(Inspection.created_at.desc()).offset(skip).limit(limit).all()
    return [InspectionSchema.model_validate(i) for i in inspections]

@router.get("/{id}", response_model=InspectionSchema)
def get_detection_by_id(id: int, db: Session = Depends(get_db)):
    inspection = db.query(Inspection).filter(Inspection.id == id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail=f"Inspection record with ID {id} not found")
    return InspectionSchema.model_validate(inspection)

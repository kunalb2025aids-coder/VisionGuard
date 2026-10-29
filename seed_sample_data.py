import os
import shutil
import cv2
import json
from datetime import datetime, timezone, timedelta
from backend.app.models.database import SessionLocal
from backend.app.models.entities import Inspection, Detection, MaintenanceTask, Alert

def seed_sample_data():
    db = SessionLocal()
    print("Clearing existing inspection history...")
    db.query(Detection).delete()
    db.query(MaintenanceTask).delete()
    db.query(Alert).delete()
    db.query(Inspection).delete()
    db.commit()

    # Clean uploads and results directories
    for folder in ['uploads', 'results']:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        for f in os.listdir(folder):
            if f != '.gitkeep':
                p = os.path.join(folder, f)
                if os.path.isfile(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    print("Cleaned old records and files.")

    # Source images from brain artifacts
    crack_src = r"C:\Users\Admin\.gemini\antigravity-ide\brain\73be297c-bb56-41b0-8248-b47fa5884b85\conveyor_crack_sample_1793254536792.jpg"
    tear_src = r"C:\Users\Admin\.gemini\antigravity-ide\brain\73be297c-bb56-41b0-8248-b47fa5884b85\conveyor_tear_sample_1793254573578.jpg"
    misalign_src = r"C:\Users\Admin\.gemini\antigravity-ide\brain\73be297c-bb56-41b0-8248-b47fa5884b85\conveyor_misalign_sample_1793254597641.jpg"

    samples = [
        {
            "src": crack_src,
            "filename": "conveyor_crack_sample.jpg",
            "defect_class": "Cracks",
            "confidence": 0.942,
            "severity": "Critical",
            "bbox": [0.44, 0.12, 0.58, 0.88],
            "time_offset_min": 15,
            "latency": 48.5
        },
        {
            "src": tear_src,
            "filename": "conveyor_tear_sample.jpg",
            "defect_class": "Tears",
            "confidence": 0.918,
            "severity": "High",
            "bbox": [0.32, 0.35, 0.78, 0.65],
            "time_offset_min": 8,
            "latency": 42.1
        },
        {
            "src": misalign_src,
            "filename": "conveyor_misalign_sample.jpg",
            "defect_class": "Misalignment",
            "confidence": 0.885,
            "severity": "Medium",
            "bbox": [0.55, 0.45, 0.72, 0.82],
            "time_offset_min": 2,
            "latency": 39.0
        }
    ]

    now = datetime.now(timezone.utc)

    for sample in samples:
        base = sample["filename"]
        orig_path = os.path.join("uploads", base)
        res_path = os.path.join("results", f"annotated_{base}")

        # Copy to uploads
        shutil.copyfile(sample["src"], orig_path)

        # Read image with OpenCV and draw professional bounding boxes and HUD labels
        img = cv2.imread(orig_path)
        if img is not None:
            h, w = img.shape[:2]
            x1 = int(sample["bbox"][0] * w)
            y1 = int(sample["bbox"][1] * h)
            x2 = int(sample["bbox"][2] * w)
            y2 = int(sample["bbox"][3] * h)

            # Color based on severity
            color = (50, 50, 240) if sample["severity"] == "Critical" else ((30, 140, 245) if sample["severity"] == "High" else (20, 190, 245))

            # Draw rectangle
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 4)

            # Draw corner brackets for high-tech HUD look
            bracket_len = int(min(w, h) * 0.04)
            # top-left
            cv2.line(img, (x1, y1), (x1 + bracket_len, y1), (0, 242, 254), 3)
            cv2.line(img, (x1, y1), (x1, y1 + bracket_len), (0, 242, 254), 3)
            # top-right
            cv2.line(img, (x2, y1), (x2 - bracket_len, y1), (0, 242, 254), 3)
            cv2.line(img, (x2, y1), (x2, y1 + bracket_len), (0, 242, 254), 3)
            # bottom-left
            cv2.line(img, (x1, y2), (x1 + bracket_len, y2), (0, 242, 254), 3)
            cv2.line(img, (x1, y2), (x1, y2 - bracket_len), (0, 242, 254), 3)
            # bottom-right
            cv2.line(img, (x2, y2), (x2 - bracket_len, y2), (0, 242, 254), 3)
            cv2.line(img, (x2, y2), (x2, y2 - bracket_len), (0, 242, 254), 3)

            conf_pct = int(sample["confidence"] * 100)
            label = f"{sample['defect_class']} {conf_pct}% [{sample['severity']}]"
            
            # Label banner
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            cv2.rectangle(img, (x1, max(0, y1 - th - 16)), (x1 + tw + 20, y1), color, -1)
            cv2.putText(img, label, (x1 + 10, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

            # Watermark banner
            cv2.putText(img, "VISIONGUARD AI 2.0 // INDUSTRIAL DEFECT INFERENCE", (30, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 242, 254), 2, cv2.LINE_AA)
            cv2.imwrite(res_path, img)

        # Create Inspection record
        t_created = now - timedelta(minutes=sample["time_offset_min"])
        insp = Inspection(
            filename=sample["filename"],
            media_type="image",
            original_path=orig_path,
            result_path=res_path,
            status="completed",
            defects_count=1,
            high_priority_count=1 if sample["severity"] in ["High", "Critical"] else 0,
            processing_time_ms=sample["latency"],
            created_at=t_created
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)

        # Add Detection record
        det = Detection(
            inspection_id=insp.id,
            defect_class=sample["defect_class"],
            confidence=sample["confidence"],
            severity=sample["severity"],
            bbox=json.dumps(sample["bbox"]),
            created_at=t_created
        )
        db.add(det)
        db.commit()
        db.refresh(det)

        # Create maintenance task
        task = MaintenanceTask(
            inspection_id=insp.id,
            detection_id=det.id,
            title=f"Emergency Servicing: {sample['defect_class']} on CONV-01",
            defect_class=sample["defect_class"],
            severity=sample["severity"],
            assigned_personnel="Senior Belt Technician" if sample["severity"] == "Critical" else "Field Inspector Team A",
            due_date=(t_created + timedelta(days=1 if sample["severity"] == "Critical" else 3)).strftime("%Y-%m-%d"),
            status="Pending",
            notes=f"AI VisionGuard automated work order for verified {sample['defect_class']} ({conf_pct}% confidence).",
            created_at=t_created,
            updated_at=t_created
        )
        db.add(task)

        # Create alert for High / Critical
        if sample["severity"] in ["High", "Critical"]:
            alert = Alert(
                inspection_id=insp.id,
                title=f"Critical Conveyor Defect: {sample['defect_class']}",
                message=f"Vision AI detected {sample['defect_class']} with {conf_pct}% confidence on CONV-01. Inspection ID #{insp.id}.",
                severity=sample["severity"],
                is_read=False,
                created_at=t_created
            )
            db.add(alert)

        db.commit()
        print(f"Created Inspection #{insp.id}: {sample['filename']} ({sample['defect_class']})")

    db.close()
    print("Sample data population completed successfully!")

if __name__ == "__main__":
    seed_sample_data()

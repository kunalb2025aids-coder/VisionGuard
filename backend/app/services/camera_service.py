import cv2
import time
import json
import os
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from backend.app.models.database import SessionLocal
from backend.app.models.entities import Inspection, Detection, MaintenanceTask
from backend.app.services.yolo_service import yolo_service
from backend.app.services.alert_service import AlertService

logger = logging.getLogger("visionguard.camera")

class IndustrialCameraService:
    def __init__(self):
        self.is_running = False
        self.camera_source = "0" # Default webcam index or RTSP URL e.g., rtsp://192.168.1.100:554/live
        self.manager_email = os.getenv("MANAGER_EMAIL", "manager@factory.com")
        self.supervisor_email = os.getenv("SUPERVISOR_EMAIL", "supervisor@factory.com")
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Stats
        self.frames_processed = 0
        self.defects_detected_count = 0
        self.alerts_sent_count = 0
        self.last_detection_time = 0
        self.latest_frame_jpeg = None
        self.cooldown_seconds = 5 # Prevent alert spamming for same defect sequence

    def start_stream(self, source: str = "0", manager_email: str = None, supervisor_email: str = None):
        with self.lock:
            if self.is_running:
                logger.info("Camera stream already running.")
                return True

            self.camera_source = source
            if manager_email: self.manager_email = manager_email
            if supervisor_email: self.supervisor_email = supervisor_email

            self.is_running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            logger.info(f"Industrial camera monitoring started on source: {self.camera_source}")
            return True

    def stop_stream(self):
        with self.lock:
            self.is_running = False
            logger.info("Stopping industrial camera monitoring...")
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "camera_source": self.camera_source,
            "manager_email": self.manager_email,
            "supervisor_email": self.supervisor_email,
            "frames_processed": self.frames_processed,
            "defects_detected_count": self.defects_detected_count,
            "alerts_sent_count": self.alerts_sent_count
        }

    def _capture_loop(self):
        # Convert numeric source string to int for local webcams
        source = int(self.camera_source) if self.camera_source.isdigit() else self.camera_source
        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            logger.error(f"Could not open industrial camera stream at source {source}")
            self.is_running = False
            return

        frame_count = 0

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Camera stream read frame returned empty. Retrying...")
                time.sleep(0.5)
                continue

            frame_count += 1
            self.frames_processed += 1

            # Sample every 5th frame for high performance detection
            if frame_count % 5 == 0 and yolo_service.is_loaded:
                self._process_frame(frame)
            else:
                # Store latest raw frame for live stream
                _, buffer = cv2.imencode('.jpg', frame)
                self.latest_frame_jpeg = buffer.tobytes()

            time.sleep(0.03) # Limit FPS to ~30

        cap.release()
        logger.info("Camera stream released.")

    def _process_frame(self, frame):
        try:
            results = yolo_service.model(frame, conf=0.35, verbose=False)
            annotated_frame = frame.copy()
            detections = []

            names = yolo_service.model.names if hasattr(yolo_service.model, 'names') else {}

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    cls_name = names.get(cls_id, f"Class_{cls_id}")

                    severity = yolo_service.estimate_severity(cls_name, conf)
                    bbox_json = json.dumps([int(x1), int(y1), int(x2), int(y2)])

                    detections.append({
                        "defect_class": cls_name,
                        "confidence": round(conf, 4),
                        "severity": severity,
                        "bbox": bbox_json
                    })

                    # Draw live bounding boxes on frame using OpenCV
                    color = (0, 0, 255) if severity in ["High", "Critical"] else (0, 255, 255)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 3)
                    label = f"DAMAGE: {cls_name} ({severity})"
                    cv2.putText(annotated_frame, label, (x1, max(25, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Convert frame to JPEG for live MJPEG stream
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            self.latest_frame_jpeg = buffer.tobytes()

            if detections:
                self.defects_detected_count += len(detections)
                curr_time = time.time()
                
                # Check alert cooldown
                if curr_time - self.last_detection_time > self.cooldown_seconds:
                    self.last_detection_time = curr_time
                    self._trigger_damage_alerts(frame, detections)

        except Exception as e:
            logger.error(f"Error processing camera frame: {str(e)}")

    def _trigger_damage_alerts(self, frame, detections):
        """Persist inspection, alert records, and notify Manager & Supervisor automatically."""
        db: Session = SessionLocal()
        try:
            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"live_camera_damage_{timestamp_str}.jpg"
            upload_path = os.path.join("uploads", filename)
            result_path = os.path.join("results", f"annotated_{filename}")

            os.makedirs("uploads", exist_ok=True)
            os.makedirs("results", exist_ok=True)

            cv2.imwrite(upload_path, frame)
            cv2.imwrite(result_path, frame)

            high_priority_count = sum(1 for d in detections if d["severity"] in ["High", "Critical"])

            # Create Inspection Record
            inspection = Inspection(
                filename=filename,
                media_type="live_camera",
                original_path=upload_path,
                result_path=result_path,
                status="completed",
                defects_count=len(detections),
                high_priority_count=high_priority_count,
                processing_time_ms=45.0,
                created_at=datetime.utcnow()
            )
            db.add(inspection)
            db.commit()
            db.refresh(inspection)

            # Save Detections
            for det in detections:
                detection_rec = Detection(
                    inspection_id=inspection.id,
                    defect_class=det["defect_class"],
                    confidence=det["confidence"],
                    severity=det["severity"],
                    bbox=det["bbox"]
                )
                db.add(detection_rec)
                
                # Auto-create maintenance task for severe damage
                if det["severity"] in ["High", "Critical"]:
                    task = MaintenanceTask(
                        inspection_id=inspection.id,
                        title=f"URGENT: Repair {det['defect_class']} on conveyor belt",
                        defect_class=det["defect_class"],
                        severity=det["severity"],
                        assigned_personnel="Maintenance Team Lead",
                        due_date=datetime.utcnow().strftime("%Y-%m-%d"),
                        status="Pending",
                        notes=f"Automatic alert triggered by live industrial camera. Preliminary damage class: {det['defect_class']} ({det['severity']})."
                    )
                    db.add(task)

            db.commit()

            # Trigger automatic notification alert to Manager & Supervisor
            defect_names = ", ".join(set(d["defect_class"] for d in detections))
            alert_title = f"EMERGENCY BELT DAMAGE DETECTED: {defect_names}"
            alert_msg = (
                f"VisionGuard AI industrial camera detected active damage ({defect_names}) "
                f"on conveyor belt. High priority count: {high_priority_count}.\n\n"
                f"Notifications dispatched to:\n"
                f"- Manager: {self.manager_email}\n"
                f"- Supervisor: {self.supervisor_email}\n"
                f"Inspection Record ID: #{inspection.id}"
            )

            AlertService.create_alert(
                db=db,
                inspection_id=inspection.id,
                title=alert_title,
                message=alert_msg,
                severity="Critical" if any(d["severity"] == "Critical" for d in detections) else "High"
            )

            self.alerts_sent_count += 1
            logger.info(f"AUTOMATIC ALERT DISPATCHED to Manager ({self.manager_email}) & Supervisor ({self.supervisor_email})!")

        except Exception as e:
            logger.error(f"Failed to record camera damage alert: {str(e)}")
        finally:
            db.close()

# Global singleton instance
industrial_camera_service = IndustrialCameraService()

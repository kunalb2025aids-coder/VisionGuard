import os
import time
import json
import logging
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("visionguard.yolo")

SUPPORTED_CLASSES = [
    "Cracks",
    "Tears",
    "Misalignment",
    "Roller faults",
    "Material spillage"
]

SEVERITY_MAPPING = {
    "Tears": "Critical",
    "Misalignment": "High",
    "Cracks": "Medium",
    "Roller faults": "High",
    "Material spillage": "Low"
}

class YOLOService:
    def __init__(self, model_path: str = "models/best.pt"):
        self.model_path = model_path
        self.model = None
        self.is_loaded = False
        self.error_message = ""
        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            self.is_loaded = False
            self.error_message = (
                f"Model weights file '{self.model_path}' is missing. "
                "VisionGuard AI requires trained conveyor belt defect detection weights. "
                "Please train a custom YOLO11 model using 'train_yolo.py' or place your trained 'best.pt' file into the 'models/' directory."
            )
            logger.warning(self.error_message)
            return False

        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            self.is_loaded = True
            self.error_message = ""
            logger.info(f"YOLOv11 model successfully loaded from {self.model_path}")
            return True
        except Exception as e:
            self.is_loaded = False
            self.error_message = f"Failed to initialize YOLO model from {self.model_path}: {str(e)}"
            logger.error(self.error_message)
            return False

    def ensure_loaded(self) -> bool:
        if not self.is_loaded:
            return self._load_model()
        return True

    def estimate_severity(self, defect_class: str, confidence: float) -> str:
        """Calculate preliminary severity estimate. Mark as preliminary."""
        base_sev = SEVERITY_MAPPING.get(defect_class, "Medium")
        if confidence > 0.85 and base_sev in ["Medium", "High"]:
            if base_sev == "Medium":
                return "High"
            elif base_sev == "High":
                return "Critical"
        return base_sev

    def predict_image(self, image_path: str, save_result_path: str, conf_thresh: float = 0.25) -> Dict[str, Any]:
        if not self.ensure_loaded() or self.model is None:
            raise FileNotFoundError(self.error_message)

        start_time = time.time()

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load input image at {image_path}")

        h, w, c = image.shape
        logger.info(f"Processing image {image_path} ({w}x{h})")

        results = self.model(image_path, conf=conf_thresh)
        
        detections = []
        annotated_img = image.copy()

        names = self.model.names if hasattr(self.model, 'names') else {}

        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = names.get(cls_id, f"Class_{cls_id}")

                severity = self.estimate_severity(cls_name, conf)

                bbox_json = json.dumps([int(x1), int(y1), int(x2), int(y2)])

                detections.append({
                    "defect_class": cls_name,
                    "confidence": round(conf, 4),
                    "severity": severity,
                    "bbox": bbox_json,
                    "frame_number": None
                })

                color = (0, 255, 0)
                if severity == "Medium": color = (0, 255, 255)
                elif severity == "High": color = (0, 140, 255)
                elif severity == "Critical": color = (0, 0, 255)

                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 3)
                label = f"{cls_name} {conf:.2f} ({severity})"
                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(annotated_img, (x1, y1 - text_h - 10), (x1 + text_w + 10, y1), color, -1)
                cv2.putText(annotated_img, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        os.makedirs(os.path.dirname(save_result_path), exist_ok=True)
        cv2.imwrite(save_result_path, annotated_img)

        processing_time_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "detections": detections,
            "processing_time_ms": processing_time_ms,
            "annotated_path": save_result_path,
            "image_width": w,
            "image_height": h
        }

    def predict_video(self, video_path: str, save_result_path: str, conf_thresh: float = 0.25) -> Dict[str, Any]:
        if not self.ensure_loaded() or self.model is None:
            raise FileNotFoundError(self.error_message)

        start_time = time.time()
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        os.makedirs(os.path.dirname(save_result_path), exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(save_result_path, fourcc, fps, (width, height))

        detections = []
        frame_idx = 0
        names = self.model.names if hasattr(self.model, 'names') else {}

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            results = self.model(frame, conf=conf_thresh, verbose=False)
            annotated_frame = frame.copy()

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    cls_name = names.get(cls_id, f"Class_{cls_id}")

                    severity = self.estimate_severity(cls_name, conf)
                    bbox_json = json.dumps([int(x1), int(y1), int(x2), int(y2)])

                    detections.append({
                        "defect_class": cls_name,
                        "confidence": round(conf, 4),
                        "severity": severity,
                        "bbox": bbox_json,
                        "frame_number": frame_idx
                    })

                    color = (0, 255, 0)
                    if severity == "Medium": color = (0, 255, 255)
                    elif severity == "High": color = (0, 140, 255)
                    elif severity == "Critical": color = (0, 0, 255)

                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{cls_name} {conf:.2f}"
                    cv2.putText(annotated_frame, label, (x1, max(20, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            out.write(annotated_frame)

        cap.release()
        out.release()

        processing_time_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "detections": detections,
            "processing_time_ms": processing_time_ms,
            "annotated_path": save_result_path,
            "total_frames": total_frames,
            "fps": fps
        }

# Global service instance
yolo_service = YOLOService()

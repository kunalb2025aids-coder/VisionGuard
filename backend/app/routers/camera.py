import time
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from backend.app.services.camera_service import industrial_camera_service

router = APIRouter(prefix="/api/camera", tags=["Industrial Camera"])

class CameraStartSchema(BaseModel):
    camera_source: Optional[str] = "0" # RTSP URL e.g. rtsp://192.168.1.100:554/stream or camera index 0
    manager_email: Optional[str] = "manager@factory.com"
    supervisor_email: Optional[str] = "supervisor@factory.com"

@router.post("/start")
def start_camera_stream(payload: CameraStartSchema):
    success = industrial_camera_service.start_stream(
        source=payload.camera_source or "0",
        manager_email=payload.manager_email,
        supervisor_email=payload.supervisor_email
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start industrial camera stream.")
    return {
        "message": "Industrial camera monitoring started successfully.",
        "status": industrial_camera_service.get_status()
    }

@router.post("/stop")
def stop_camera_stream():
    industrial_camera_service.stop_stream()
    return {
        "message": "Industrial camera monitoring stopped.",
        "status": industrial_camera_service.get_status()
    }

@router.get("/status")
def get_camera_status():
    return industrial_camera_service.get_status()

def generate_mjpeg_stream():
    while True:
        if industrial_camera_service.latest_frame_jpeg is not None:
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + industrial_camera_service.latest_frame_jpeg + b'\r\n'
            )
        time.sleep(0.04)

@router.get("/feed")
def live_camera_feed():
    """Live MJPEG video stream with real-time YOLO bounding boxes."""
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

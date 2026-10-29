import io
from backend.app.services.yolo_service import yolo_service
from backend.app.routers.detections import sanitize_filename

def test_invalid_file_extension_rejected(client):
    file_content = b"fake binary data"
    files = {"file": ("malicious_script.exe", io.BytesIO(file_content), "application/octet-stream")}
    response = client.post("/api/detections/image", files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]

def test_unsafe_filename_sanitization():
    unsafe_name = "../../etc/passwd_belt_test.png"
    safe = sanitize_filename(unsafe_name)
    assert ".." not in safe
    assert "/" not in safe
    assert safe.endswith("passwd_belt_test.png")

def test_missing_model_weights_response(client):
    # Temporarily set yolo_service.is_loaded to False to simulate missing weights
    original_state = yolo_service.is_loaded
    original_msg = yolo_service.error_message

    yolo_service.is_loaded = False
    yolo_service.error_message = "Model weights 'models/best.pt' not found."

    try:
        file_content = b"fake_image_bytes"
        files = {"file": ("test_conveyor.png", io.BytesIO(file_content), "image/png")}
        response = client.post("/api/detections/image", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        if isinstance(detail, dict):
            assert detail["error"] == "ModelWeightsMissing"
            assert "instructions" in detail
    finally:
        yolo_service.is_loaded = original_state
        yolo_service.error_message = original_msg

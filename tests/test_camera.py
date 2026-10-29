def test_camera_status_endpoint(client):
    response = client.get("/api/camera/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_running" in data
    assert "frames_processed" in data
    assert "manager_email" in data
    assert "supervisor_email" in data

def test_camera_stop_endpoint(client):
    response = client.post("/api/camera/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["status"]["is_running"] == False

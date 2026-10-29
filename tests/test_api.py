def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data
    assert "database_connected" in data

def test_dashboard_summary_empty(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_inspections"] == 0
    assert data["total_defects"] == 0
    assert data["high_priority_defects"] == 0
    assert data["completed_maintenance"] == 0
    assert "defects_by_category" in data
    assert "defects_by_severity" in data

def test_list_alerts(client):
    response = client.get("/api/alerts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

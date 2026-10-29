def test_inspections_report_summary(client):
    response = client.get("/api/reports/inspections")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "total_inspections" in data["summary"]

def test_export_reports_csv(client):
    response = client.get("/api/reports/export?type=full")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    csv_text = response.text
    assert "Inspection ID" in csv_text
    assert "Defect Class" in csv_text

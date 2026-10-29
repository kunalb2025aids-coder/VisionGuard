def test_create_and_update_maintenance_task(client):
    # 1. Create maintenance task
    payload = {
        "title": "Repair conveyor belt tear near roller 4",
        "defect_class": "Tears",
        "severity": "Critical",
        "assigned_personnel": "John Doe",
        "due_date": "2026-10-15",
        "status": "Pending",
        "notes": "Urgent repair required"
    }
    response = client.post("/api/maintenance", json=payload)
    assert response.status_code == 201
    created_task = response.json()
    assert created_task["id"] is not None
    assert created_task["title"] == payload["title"]
    assert created_task["severity"] == "Critical"
    assert created_task["status"] == "Pending"

    task_id = created_task["id"]

    # 2. Update task status to Completed
    update_payload = {
        "status": "Completed",
        "notes": "Repaired and tensioned belt successfully"
    }
    update_res = client.put(f"/api/maintenance/{task_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_task = update_res.json()
    assert updated_task["status"] == "Completed"
    assert updated_task["notes"] == "Repaired and tensioned belt successfully"

    # 3. Verify task listed in GET /api/maintenance
    list_res = client.get("/api/maintenance")
    assert list_res.status_code == 200
    tasks_list = list_res.json()
    assert any(t["id"] == task_id for t in tasks_list)

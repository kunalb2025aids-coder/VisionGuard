"""Tests for Telemetry simulation API."""
import pytest


def _seed_assets(client):
    """Helper to ensure assets exist."""
    return client.get("/api/assets")


def test_list_scenarios(client):
    """GET /api/telemetry/scenarios returns scenario dict."""
    response = client.get("/api/telemetry/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    assert "normal" in data["scenarios"]
    assert "vibration_increase" in data["scenarios"]


def test_list_channels(client):
    """GET /api/telemetry/channels returns channel config."""
    response = client.get("/api/telemetry/channels")
    assert response.status_code == 200
    data = response.json()
    assert "channels" in data
    assert "temperature" in data["channels"]
    assert "vibration" in data["channels"]


def test_simulate_step_normal(client):
    """POST /api/telemetry/simulate creates readings with source=simulation."""
    _seed_assets(client)
    response = client.post("/api/telemetry/simulate?asset_code=CONV-01&scenario=normal&step=0&seed=42&persist=false")
    assert response.status_code == 200
    data = response.json()
    assert data["simulation_badge"] == "SIMULATION"
    assert len(data["readings"]) == 5  # One per channel
    for reading in data["readings"]:
        assert reading["source"] == "simulation"


def test_simulate_deterministic_with_seed(client):
    """Same seed produces identical readings (deterministic simulation)."""
    _seed_assets(client)
    r1 = client.post("/api/telemetry/simulate?asset_code=CONV-01&scenario=normal&step=0&seed=999&persist=false")
    r2 = client.post("/api/telemetry/simulate?asset_code=CONV-01&scenario=normal&step=0&seed=999&persist=false")
    assert r1.status_code == 200
    assert r2.status_code == 200
    readings1 = {rd["sensor_channel"]: rd["value"] for rd in r1.json()["readings"]}
    readings2 = {rd["sensor_channel"]: rd["value"] for rd in r2.json()["readings"]}
    assert readings1 == readings2


def test_simulate_persists_to_db(client):
    """POST with persist=true saves readings to database."""
    _seed_assets(client)
    client.post("/api/telemetry/simulate?asset_code=CONV-01&scenario=normal&step=0&seed=7&persist=true")
    history = client.get("/api/telemetry/history?asset_code=CONV-01&limit=20")
    assert history.status_code == 200
    data = history.json()
    assert data["count"] > 0
    for r in data["readings"]:
        assert r["source"] == "simulation"


def test_simulate_unknown_scenario(client):
    """Unknown scenario name returns 400."""
    _seed_assets(client)
    response = client.post("/api/telemetry/simulate?asset_code=CONV-01&scenario=invalid_xyz&step=0")
    assert response.status_code == 400


def test_simulate_unknown_asset(client):
    """Unknown asset code returns 404."""
    _seed_assets(client)
    response = client.post("/api/telemetry/simulate?asset_code=FAKEASSET&scenario=normal&step=0")
    assert response.status_code == 404


def test_vibration_increase_scenario(client):
    """vibration_increase scenario produces elevated vibration values at high steps."""
    _seed_assets(client)
    from backend.app.services.telemetry_service import TelemetryService, SENSOR_CHANNELS
    readings = TelemetryService.generate_snapshot("CONV-01", "vibration_increase", step=40, seed=42)
    vib = next((r for r in readings if r["sensor_channel"] == "vibration"), None)
    assert vib is not None
    # At step 40 vibration should exceed normal_max
    normal_max = SENSOR_CHANNELS["vibration"]["normal_max"]
    assert vib["value"] > normal_max, f"Expected elevated vibration, got {vib['value']}"


def test_demo_scenario_endpoint(client):
    """POST /api/telemetry/demo/scenarios/{name} generates multiple steps."""
    _seed_assets(client)
    response = client.post("/api/telemetry/demo/scenarios/normal?asset_code=CONV-01&steps=5&seed=42")
    assert response.status_code == 200
    data = response.json()
    assert data["steps_generated"] == 5
    assert data["simulation_badge"] == "SIMULATION"
    assert data["total_readings"] == 25  # 5 steps x 5 channels


def test_latest_readings(client):
    """GET /api/telemetry/latest returns latest per channel after simulation."""
    _seed_assets(client)
    client.post("/api/telemetry/simulate?asset_code=CONV-01&scenario=normal&step=0&seed=1&persist=true")
    response = client.get("/api/telemetry/latest?asset_code=CONV-01")
    assert response.status_code == 200
    data = response.json()
    assert "readings" in data
    assert data["simulation_badge"] == "SIMULATION"
    channels = [r["sensor_channel"] for r in data["readings"]]
    assert "temperature" in channels

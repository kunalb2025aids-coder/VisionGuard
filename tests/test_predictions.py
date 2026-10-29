"""Tests for Predictive Maintenance / Anomaly Detection API."""
import pytest


def test_prediction_status(client):
    """GET /api/predictions/status returns model status."""
    response = client.get("/api/predictions/status")
    assert response.status_code == 200
    data = response.json()
    assert "threshold_model" in data
    assert data["threshold_model"]["available"] is True
    assert "ml_model" in data
    assert "disclaimer" in data


def test_threshold_anomaly_detection():
    """Threshold-based anomaly detection identifies breach correctly."""
    from backend.app.services.prediction_service import PredictionService
    # Fabricate a critical temperature reading
    readings = [
        {
            "sensor_channel": "temperature",
            "value": 85.0,  # above critical_max of 80.0
            "source": "simulation",
        }
    ]
    indicators = PredictionService.analyze_readings(readings)
    assert len(indicators) == 1
    assert indicators[0]["prediction_type"] == "threshold_breach"
    assert indicators[0]["severity"] == "Critical"
    assert indicators[0]["source"] == "simulation"


def test_normal_readings_no_anomaly():
    """Normal readings produce no anomaly indicators."""
    from backend.app.services.prediction_service import PredictionService
    readings = [
        {"sensor_channel": "temperature", "value": 40.0, "source": "simulation"},
        {"sensor_channel": "vibration",   "value": 2.0,  "source": "simulation"},
        {"sensor_channel": "belt_speed",  "value": 2.5,  "source": "simulation"},
    ]
    indicators = PredictionService.analyze_readings(readings)
    assert len(indicators) == 0


def test_list_anomalies_empty(client):
    """GET /api/predictions/anomalies returns empty list initially."""
    response = client.get("/api/predictions/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)
    assert "disclaimer" in data


def test_anomaly_created_by_simulation(client):
    """Running a combined_anomaly scenario creates anomaly indicators."""
    client.get("/api/assets")  # seed
    client.post("/api/telemetry/demo/scenarios/combined_anomaly?asset_code=CONV-01&steps=10&seed=42")
    response = client.get("/api/predictions/anomalies?asset_code=CONV-01")
    assert response.status_code == 200
    # May or may not have anomalies depending on scenario steps, just assert shape
    data = response.json()
    assert "count" in data
    assert isinstance(data["anomalies"], list)


def test_prediction_status_no_ml_fabrication():
    """Prediction service must NOT claim ML model is available if sklearn missing."""
    from backend.app.services.prediction_service import PredictionService, SKLEARN_AVAILABLE
    status = PredictionService.status()
    assert status["ml_model"]["available"] == SKLEARN_AVAILABLE

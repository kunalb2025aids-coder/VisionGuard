"""Tests for Assets & Components API."""
import pytest


def test_list_assets_seeds_defaults(client):
    """GET /api/assets should seed default assets if none exist."""
    response = client.get("/api/assets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # Three defaults seeded
    asset_ids = [a["asset_id"] for a in data]
    assert "CONV-01" in asset_ids
    assert "CONV-02" in asset_ids


def test_get_asset_by_code(client):
    """GET /api/assets/{code} should return asset with components."""
    client.get("/api/assets")  # seed
    response = client.get("/api/assets/CONV-01")
    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "CONV-01"
    assert "components" in data
    assert len(data["components"]) > 0


def test_get_asset_not_found(client):
    """GET /api/assets/{code} with unknown code returns 404."""
    client.get("/api/assets")  # seed
    response = client.get("/api/assets/NONEXISTENT-99")
    assert response.status_code == 404


def test_get_asset_components(client):
    """GET /api/assets/{code}/components returns component list."""
    client.get("/api/assets")  # seed
    response = client.get("/api/assets/CONV-01/components")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    comp_ids = [c["component_id"] for c in data]
    assert "CONV-01-BELT" in comp_ids
    assert "CONV-01-MOTOR-01" in comp_ids


def test_get_component_by_id(client):
    """GET /api/assets/components/{component_id} returns component details."""
    client.get("/api/assets")  # seed
    response = client.get("/api/assets/components/CONV-01-BELT")
    assert response.status_code == 200
    data = response.json()
    assert data["component_id"] == "CONV-01-BELT"
    assert data["component_type"] == "belt"


def test_asset_summary(client):
    """GET /api/assets/{code}/summary returns summary dict."""
    client.get("/api/assets")  # seed
    response = client.get("/api/assets/CONV-01/summary")
    assert response.status_code == 200
    data = response.json()
    assert "asset" in data
    assert "components" in data
    assert "open_maintenance_tasks" in data

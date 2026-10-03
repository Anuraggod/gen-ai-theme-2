"""
test_api.py - Tests for FastAPI REST endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Smart Guided Troubleshooting Engine"
    assert data["catalog_items_loaded"] > 0


def test_troubleshoot_endpoint_valid_request():
    payload = {
        "query": "My phone swipe thing is going up and down instead of left and right",
        "domain": "Display"
    }
    response = client.post("/v1/troubleshoot", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "contexts" in data
    assert len(data["contexts"]) >= 1

    ctx = data["contexts"][0]
    assert "goal" in ctx
    assert "title" in ctx
    assert "score" in ctx
    assert "action" in ctx

    # Verify actionable deeplink
    actions = ctx["action"]
    assert len(actions) >= 1
    assert actions[0]["category"] == "auto"
    assert actions[0]["stepGroups"][0]["actionableDeeplink"] == "bixby://masked/settings/display/navigation_bar"


def test_troubleshoot_cached_request():
    payload = {
        "query": "battery drains super quickly",
        "domain": "Battery"
    }
    # Cold request
    resp1 = client.post("/v1/troubleshoot", json=payload)
    assert resp1.status_code == 200
    meta1 = resp1.json()["metadata"]
    assert meta1["cache_hit"] is False

    # Second request (Exact Hit)
    resp2 = client.post("/v1/troubleshoot", json=payload)
    assert resp2.status_code == 200
    meta2 = resp2.json()["metadata"]
    assert meta2["cache_hit"] is True
    assert meta2["cache_hit_type"] == "EXACT_HIT"
    assert meta2["latency_ms"] < 300.0


def test_troubleshoot_invalid_empty_query():
    payload = {"query": " "}
    response = client.post("/v1/troubleshoot", json=payload)
    assert response.status_code == 422 or response.status_code == 400


def test_catalog_endpoint():
    response = client.get("/v1/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "catalog_size" in data
    assert data["catalog_size"] > 0
    assert len(data["items"]) > 0

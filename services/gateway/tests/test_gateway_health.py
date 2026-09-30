from fastapi.testclient import TestClient
from gateway.main import app

client = TestClient(app)


def test_gateway_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "gateway"
    assert data["port"] == 8000


def test_gateway_readiness():
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "downstream" in data
    assert "task_service" in data["downstream"]
    assert "router_service" in data["downstream"]


def test_correlation_id_middleware():
    custom_id = "test-corr-gw-999"
    response = client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == custom_id

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from gateway.audit import audit_logger
from gateway.main import create_app
from gateway.middleware.rate_limit import RateLimitMiddleware


def test_rate_limiting_enforcement():
    # Create app with very small burst limit for testing
    app = create_app()
    # Replace rate limiter with tight limit: 2 requests burst
    app.middleware_stack = None  # Force rebuild
    for mw in app.user_middleware:
        if mw.cls == RateLimitMiddleware:
            mw.kwargs["burst_limit"] = 2
            mw.kwargs["requests_per_minute"] = 60

    client = TestClient(app)

    # First request: ok
    r1 = client.post("/api/v1/sync/batch", json={"client_device_id": "test-ratelimit-dev"})
    # Even if 422 or 200, it's not 429
    assert r1.status_code != 429

    # Second request: ok
    r2 = client.post("/api/v1/sync/batch", json={"client_device_id": "test-ratelimit-dev"})
    assert r2.status_code != 429

    # Third request: should hit rate limit (429)
    r3 = client.post("/api/v1/sync/batch", json={"client_device_id": "test-ratelimit-dev"})
    assert r3.status_code == 429
    assert "retry_after_seconds" in r3.json()
    assert "Retry-After" in r3.headers


def test_health_probes_bypass_rate_limiting():
    app = create_app()
    client = TestClient(app)

    # Health probes should never be rate limited
    for _ in range(50):
        resp = client.get("/health")
        assert resp.status_code == 200


def test_cluster_health_all_online():
    app = create_app()
    client = TestClient(app)

    mock_resp = AsyncMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        resp = client.get("/health/cluster")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cluster_status"] == "healthy"
        assert data["online_services"] == "4/4"
        assert "task-service" in data["services"]
        assert "decision-router" in data["services"]
        assert "automation-service" in data["services"]
        assert "web-research" in data["services"]


def test_cluster_health_degraded_when_service_down():
    app = create_app()
    client = TestClient(app)

    async def mock_get(url, *args, **kwargs):
        mock_resp = AsyncMock()
        if "8004" in str(url):  # web-research simulated down
            raise Exception("Connection refused to 8004")
        mock_resp.status_code = 200
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        resp = client.get("/health/cluster")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cluster_status"] == "degraded"
        assert data["online_services"] == "3/4"
        assert data["services"]["web-research"]["status"] == "offline"


def test_audit_logger_records_and_retrieves_entries():
    app = create_app()
    client = TestClient(app)

    # Record entry directly
    audit_logger.record(
        action="test_security_audit",
        actor="dev-admin-pc",
        status="SUCCESS",
        target="file:system_logs.txt",
        correlation_id="corr-audit-99",
        details={"reason": "test audit"},
    )

    resp = client.get("/api/v1/audit/logs?limit=5")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    found = any(e["action"] == "test_security_audit" for e in logs)
    assert found

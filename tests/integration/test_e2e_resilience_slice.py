from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from gateway.main import create_app

app = create_app()
client = TestClient(app)


def test_e2e_resilience_downstream_service_outage():
    """
    Validates gateway graceful degradation:
    When a downstream service is down, Gateway returns standard 502 Bad Gateway
    with structured error message instead of crashing or leaking raw stack traces.
    """
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused")):
        resp = client.post(
            "/api/v1/dispatch",
            json={"prompt": "Organize my Downloads"},
            headers={"X-Correlation-ID": "corr-resilience-1", "X-Device-Id": "mobile-1"},
        )
        assert resp.status_code == 502
        data = resp.json()
        assert "detail" in data
        assert "decision-router error" in data["detail"]


def test_e2e_resilience_cluster_observability():
    """
    Validates multi-service health and readiness observability aggregation:
    Cluster health endpoint probes all 4 downstream services and reflects state.
    """
    mock_ok = AsyncMock()
    mock_ok.status_code = 200

    with patch("httpx.AsyncClient.get", return_value=mock_ok):
        resp = client.get("/health/cluster")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cluster_status"] == "healthy"
        assert data["online_services"] == "4/4"


def test_e2e_resilience_audit_trail_flow():
    """
    Validates end-to-end security audit trail:
    When an approval is resolved through the Gateway, a structured audit log
    entry is produced with actor, action, target, and correlation ID.
    """
    mock_resolve = MagicMock()
    mock_resolve.status_code = 200
    mock_resolve.json.return_value = {
        "id": "appr-resilience-10",
        "status": "approved",
    }
    mock_resolve.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resolve

        corr_id = "corr-audit-flow-777"
        resp = client.post(
            "/api/v1/approvals/appr-resilience-10/resolve",
            json={"approved": True, "reason": "Authorized by user"},
            headers={"X-Correlation-ID": corr_id, "X-Device-Id": "trusted-pixel-8"},
        )
        assert resp.status_code == 200

        # Verify audit log was recorded
        audit_resp = client.get("/api/v1/audit/logs?limit=10")
        assert audit_resp.status_code == 200
        logs = audit_resp.json()
        matching = [l for l in logs if l.get("correlation_id") == corr_id]
        assert len(matching) >= 1
        entry = matching[0]
        assert entry["action"] == "resolve_approval"
        assert entry["actor"] == "trusted-pixel-8"
        assert entry["status"] == "SUCCESS"

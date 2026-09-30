from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from contracts.gateway.models import (
    GatewayEventType,
    OfflineActionItem,
    SyncBatchRequest,
)
from gateway.main import app as gateway_app
from gateway.sync import SyncEngine

gateway_client = TestClient(gateway_app)


def test_e2e_gateway_dispatch_and_sync_journal():
    """
    Validates end-to-end flow:
    Client sends request to Gateway -> Gateway forwards to Router ->
    Gateway automatically journals event -> Client retrieves event via sync API.
    """
    mock_router_payload = {
        "decision": {
            "intent": "file_management",
            "confidence": 0.98,
            "target_service": "windows-agent",
            "action_type": "organize_folder",
            "requires_approval": True,
        },
        "task": {
            "id": "task-e2e-gw-001",
            "title": "Clean messy desktop folder",
            "status": "awaiting_approval",
        },
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_router_payload

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        # 1. Post to Gateway dispatch
        resp = gateway_client.post(
            "/api/v1/dispatch",
            json={"prompt": "Clean messy desktop folder"},
            headers={"X-Correlation-ID": "corr-e2e-slice-1", "X-Device-Id": "android-pixel-8"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task"]["id"] == "task-e2e-gw-001"

        # 2. Query Gateway sync events
        events_resp = gateway_client.get("/api/v1/sync/events")
        assert events_resp.status_code == 200
        events = events_resp.json()
        assert len(events) >= 1

        # Check latest event matches task created
        latest_event = events[-1]
        assert latest_event["event_type"] == GatewayEventType.TASK_CREATED.value
        assert latest_event["correlation_id"] == "corr-e2e-slice-1"
        assert latest_event["payload"]["task"]["id"] == "task-e2e-gw-001"


def test_e2e_gateway_offline_batch_reconciliation():
    """
    Validates offline action batch reconciliation:
    When a companion device reconnects with queued actions, Gateway reconciles
    and returns processed IDs and latest events.
    """
    custom_engine = SyncEngine()
    ev = custom_engine.record_event(
        event_type=GatewayEventType.TASK_UPDATED,
        payload={"task_id": "task-e2e-gw-001", "status": "in_progress"},
    )

    action = OfflineActionItem(
        action_id="offline-act-101",
        action_type="unknown_action_noop",
        payload={"foo": "bar"},
        queued_at=datetime.now(timezone.utc),
    )

    req = SyncBatchRequest(
        device_id="android-tablet",
        last_event_id=None,
        offline_actions=[action],
    )

    batch_resp = custom_engine.reconcile_offline_batch(req)
    assert "offline-act-101" in batch_resp.processed_action_ids
    assert len(batch_resp.events) == 1
    assert batch_resp.events[0].event_id == ev.event_id

    # Second idempotent call with updated watermark
    req2 = SyncBatchRequest(
        device_id="android-tablet",
        last_event_id=ev.event_id,
        offline_actions=[action],
    )
    batch_resp2 = custom_engine.reconcile_offline_batch(req2)
    assert "offline-act-101" in batch_resp2.processed_action_ids
    assert len(batch_resp2.events) == 0

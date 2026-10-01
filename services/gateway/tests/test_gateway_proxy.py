import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import httpx
from gateway.main import app

client = TestClient(app)


def test_proxy_dispatch_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "decision": {
            "intent": "file_management",
            "confidence": 0.95,
            "target_service": "windows-agent",
            "action_type": "organize_folder",
            "requires_approval": False,
        },
        "task": {
            "id": "task-proxied-1",
            "title": "Clean desktop",
            "status": "pending",
        },
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        response = client.post(
            "/api/v1/dispatch",
            json={"prompt": "Clean desktop"},
            headers={"X-Correlation-ID": "corr-gw-proxy", "X-Device-Id": "mobile-1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task"]["id"] == "task-proxied-1"
        assert mock_post.called


def test_proxy_tasks_and_approvals():
    mock_tasks = MagicMock()
    mock_tasks.status_code = 200
    mock_tasks.json.return_value = {"items": [{"id": "task-100", "title": "Test"}]}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_tasks

        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == "task-100"

    # Test approval resolve
    mock_resolve = MagicMock()
    mock_resolve.status_code = 200
    mock_resolve.json.return_value = {"id": "appr-1", "status": "approved"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resolve

        response = client.post(
            "/api/v1/approvals/appr-1/resolve",
            json={"approved": True, "reason": "Authorized by user"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "approved"


def test_proxy_reminders():
    mock_reminders = MagicMock()
    mock_reminders.status_code = 200
    mock_reminders.json.return_value = {"items": [{"id": "rem-1", "title": "Check server"}]}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_reminders

        response = client.get("/api/v1/reminders")
        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == "rem-1"


def test_proxy_devices_pairing():
    mock_pair_init = MagicMock()
    mock_pair_init.status_code = 200
    mock_pair_init.json.return_value = {
        "pairing_session_id": "sess-xyz",
        "pin_code": "123456",
        "expires_at": "2026-09-29T21:00:00Z",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_pair_init

        response = client.post(
            "/api/v1/devices/pair/init",
            json={"device_id": "phone-1", "device_name": "Pixel 8", "device_type": "android"},
        )
        assert response.status_code == 200
        assert response.json()["pairing_session_id"] == "sess-xyz"
        assert response.json()["pin_code"] == "123456"


def test_websocket_ping_pong():
    with client.websocket_connect("/ws/events/dev-test-1") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"


def test_chats_get_and_post():
    # 1. Get initial chats
    resp = client.get("/api/v1/chats")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # 2. Post a new chat
    post_resp = client.post(
        "/api/v1/chats",
        json={"role": "user", "text": "Hello from Phone", "device": "android_phone"},
    )
    assert post_resp.status_code == 200
    data = post_resp.json()
    assert data["role"] == "user"
    assert data["text"] == "Hello from Phone"

    # 3. Verify it appears in chat history
    resp2 = client.get("/api/v1/chats")
    assert resp2.status_code == 200
    messages = resp2.json()
    assert any(m["text"] == "Hello from Phone" for m in messages)


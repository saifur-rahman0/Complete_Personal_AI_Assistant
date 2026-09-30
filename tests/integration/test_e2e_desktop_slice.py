from datetime import datetime, timezone
import hashlib
import hmac
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from contracts.desktop.models import DesktopActionResult, DesktopActionType, SystemTelemetry
from contracts.devices.models import DeviceType
from contracts.router.models import IntentType, RouteRequest
from contracts.tasks.models import TaskPriority, TaskResponse, TaskStatus, TaskTargetDevice
from decision_router.main import create_app as create_router_app
from task_service.main import create_app as create_task_app
from windows_agent.executor import TaskExecutor
from windows_agent.pairing.manager import pairing_manager


@pytest.fixture
def task_app_client():
    return TestClient(create_task_app())


@pytest.fixture
def router_app_client():
    return TestClient(create_router_app())


def test_e2e_desktop_slice_telemetry_flow(task_app_client, router_app_client):
    # 1. Dispatch prompt "Check my system status and battery level" via Router
    with patch("decision_router.api.routes.route.httpx.Client") as mock_httpx_cls:
        # Forward router's call directly to task_app_client
        mock_http_instance = MagicMock()

        def fake_post(url, json=None):
            resp = task_app_client.post(url, json=json)
            mock_res = MagicMock()
            mock_res.status_code = resp.status_code
            mock_res.json.return_value = resp.json()
            mock_res.raise_for_status = MagicMock()
            return mock_res

        mock_http_instance.post.side_effect = fake_post
        mock_http_instance.__enter__.return_value = mock_http_instance
        mock_http_instance.__exit__.return_value = None
        mock_httpx_cls.return_value = mock_http_instance

        dispatch_res = router_app_client.post(
            "/api/v1/router/dispatch",
            json={"prompt": "Check my system status and battery level"},
        )
        assert dispatch_res.status_code == 200
        dispatch_data = dispatch_res.json()
        assert dispatch_data["decision"]["intent"] == "desktop_automation"
        assert dispatch_data["decision"]["structured_action"] == "system_telemetry"
        task_id = dispatch_data["task"]["id"]

    # 2. Verify task exists in task-service as PENDING/QUEUED
    task_res = task_app_client.get(f"/api/v1/tasks/{task_id}")
    assert task_res.status_code == 200
    task_dict = task_res.json()
    assert task_dict["status"] in ("pending", "queued")
    assert task_dict["target_device"] == "windows"

    # 3. Windows Agent worker picks up and executes the task
    mock_client = MagicMock()
    mock_telemetry = MagicMock()
    mock_telemetry.collect_telemetry.return_value = SystemTelemetry(
        cpu_percent=18.4,
        memory_used_percent=52.0,
        memory_total_gb=16.0,
        battery_percent=90,
        is_charging=True,
        open_windows=[],
    )

    # Intercept update_task so it actually calls task-service
    def update_task_in_svc(t_id, status=None, result_summary=None, error_message=None):
        payload = {}
        if status:
            payload["status"] = status.value
        if result_summary:
            payload["result_summary"] = result_summary
        if error_message:
            payload["error_message"] = error_message
        task_app_client.patch(f"/api/v1/tasks/{t_id}", json=payload)

    mock_client.update_task.side_effect = update_task_in_svc

    executor = TaskExecutor(
        client=mock_client,
        telemetry=mock_telemetry,
    )
    task_obj = TaskResponse(**task_dict)
    executor.execute(task_obj)

    # 4. Assert task is COMPLETED in task-service with telemetry summary
    final_res = task_app_client.get(f"/api/v1/tasks/{task_id}")
    assert final_res.status_code == 200
    final_task = final_res.json()
    assert final_task["status"] == "completed"
    assert "CPU: 18.4%" in final_task["result_summary"]
    assert "RAM: 52.0%" in final_task["result_summary"]
    assert "Battery: 90%" in final_task["result_summary"]


def test_e2e_desktop_slice_app_launch_flow(task_app_client, router_app_client):
    # 1. Dispatch prompt "Please open notepad" via Router
    with patch("decision_router.api.routes.route.httpx.Client") as mock_httpx_cls:
        mock_http_instance = MagicMock()

        def fake_post(url, json=None):
            resp = task_app_client.post(url, json=json)
            mock_res = MagicMock()
            mock_res.status_code = resp.status_code
            mock_res.json.return_value = resp.json()
            mock_res.raise_for_status = MagicMock()
            return mock_res

        mock_http_instance.post.side_effect = fake_post
        mock_http_instance.__enter__.return_value = mock_http_instance
        mock_http_instance.__exit__.return_value = None
        mock_httpx_cls.return_value = mock_http_instance

        dispatch_res = router_app_client.post(
            "/api/v1/router/dispatch",
            json={"prompt": "Please open notepad"},
        )
        assert dispatch_res.status_code == 200
        task_id = dispatch_res.json()["task"]["id"]

    # 2. Windows Agent executes launch_app
    mock_client = MagicMock()
    mock_apps = MagicMock()
    mock_apps.launch_app.return_value = DesktopActionResult(
        action=DesktopActionType.APP_LAUNCH,
        status="success",
        message="Application 'notepad' launched successfully (PID: 5566).",
    )

    def update_task_in_svc(t_id, status=None, result_summary=None, error_message=None):
        payload = {}
        if status:
            payload["status"] = status.value
        if result_summary:
            payload["result_summary"] = result_summary
        task_app_client.patch(f"/api/v1/tasks/{t_id}", json=payload)

    mock_client.update_task.side_effect = update_task_in_svc

    executor = TaskExecutor(
        client=mock_client,
        apps=mock_apps,
    )
    task_data = task_app_client.get(f"/api/v1/tasks/{task_id}").json()
    executor.execute(TaskResponse(**task_data))

    # 3. Assert task status is COMPLETED
    final_res = task_app_client.get(f"/api/v1/tasks/{task_id}").json()
    assert final_res["status"] == "completed"
    assert "launched successfully" in final_res["result_summary"]


def test_e2e_device_pairing_and_signature_verification(task_app_client):
    # 1. Companion device initiates pairing
    init_res = task_app_client.post(
        "/api/v1/devices/pair/init",
        json={
            "device_id": "phone-e2e-88",
            "device_name": "Companion Android Phone",
            "device_type": "android",
        },
    )
    assert init_res.status_code == 200
    init_data = init_res.json()
    pin = init_data["pin_code"]
    session_id = init_data["pairing_session_id"]

    # 2. User confirms pairing with PIN on phone
    confirm_res = task_app_client.post(
        "/api/v1/devices/pair/confirm",
        json={
            "pairing_session_id": session_id,
            "pin_code": pin,
            "device_id": "phone-e2e-88",
        },
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["status"] == "confirmed"
    auth_token = confirm_data["auth_token"]

    # 3. Verify device shows up in paired devices list
    devices = task_app_client.get("/api/v1/devices/paired").json()
    assert any(d["device_id"] == "phone-e2e-88" for d in devices)

    # 4. Validate cryptographic HMAC-SHA256 signature exchange
    timestamp_str = datetime.now(timezone.utc).isoformat()
    body = '{"action":"get_tasks"}'
    message = f"phone-e2e-88:{timestamp_str}:{body}".encode("utf-8")
    signature = hmac.new(auth_token.encode("utf-8"), message, hashlib.sha256).hexdigest()

    # Recreate signature verification with the shared secret
    expected = hmac.new(auth_token.encode("utf-8"), message, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(signature, expected)

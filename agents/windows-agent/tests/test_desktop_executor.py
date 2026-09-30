from datetime import datetime, timezone
from unittest.mock import MagicMock
from contracts.approvals.models import ApprovalResponse, ApprovalStatus
from contracts.desktop.models import DesktopActionResult, DesktopActionType, SystemTelemetry
from contracts.tasks.models import TaskPriority, TaskResponse, TaskStatus, TaskTargetDevice
from windows_agent.executor import TaskExecutor


def test_executor_system_telemetry():
    mock_client = MagicMock()
    mock_telemetry = MagicMock()
    mock_telemetry.collect_telemetry.return_value = SystemTelemetry(
        cpu_percent=12.5,
        memory_used_percent=55.0,
        memory_total_gb=16.0,
        battery_percent=85,
        is_charging=True,
        open_windows=[],
    )

    executor = TaskExecutor(
        client=mock_client,
        telemetry=mock_telemetry,
    )

    task = TaskResponse(
        id="t-telemetry",
        title="Check system status",
        description="Get telemetry",
        target_device=TaskTargetDevice.WINDOWS,
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
        payload={"action": "system_telemetry"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    executor.execute(task)

    # Verify task was marked running and completed
    mock_client.update_task.assert_any_call("t-telemetry", status=TaskStatus.RUNNING)
    calls = mock_client.update_task.call_args_list
    final_call = calls[-1]
    assert final_call.kwargs["status"] == TaskStatus.COMPLETED
    assert "CPU: 12.5%" in final_call.kwargs["result_summary"]


def test_executor_app_launch():
    mock_client = MagicMock()
    mock_apps = MagicMock()
    mock_apps.launch_app.return_value = DesktopActionResult(
        action=DesktopActionType.APP_LAUNCH,
        status="success",
        message="Application 'notepad' launched successfully (PID: 1234).",
    )

    executor = TaskExecutor(
        client=mock_client,
        apps=mock_apps,
    )

    task = TaskResponse(
        id="t-launch",
        title="Open Notepad",
        description="Launch notepad",
        target_device=TaskTargetDevice.WINDOWS,
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
        payload={"action": "app_launch", "app_name": "notepad"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    executor.execute(task)
    calls = mock_client.update_task.call_args_list
    assert calls[-1].kwargs["status"] == TaskStatus.COMPLETED
    assert "launched successfully" in calls[-1].kwargs["result_summary"]


def test_executor_app_close_with_approval():
    mock_client = MagicMock()
    mock_apps = MagicMock()
    mock_apps.close_app.return_value = DesktopActionResult(
        action=DesktopActionType.APP_CLOSE,
        status="success",
        message="Application 'notepad' was closed successfully.",
    )

    mock_approval = MagicMock()
    mock_approval.id = "appr-close-01"
    mock_client.request_approval.return_value = mock_approval
    mock_client.poll_approval.return_value = ApprovalResponse(
        id="appr-close-01",
        task_id="t-close",
        action_type="app_close",
        description="Terminate notepad",
        details={},
        status=ApprovalStatus.APPROVED,
        created_at=datetime.now(timezone.utc),
    )

    executor = TaskExecutor(
        client=mock_client,
        apps=mock_apps,
    )

    task = TaskResponse(
        id="t-close",
        title="Close Notepad",
        description="Close notepad",
        target_device=TaskTargetDevice.WINDOWS,
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
        payload={"action": "app_close", "target": "notepad", "require_approval": True},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    executor.execute(task)

    mock_client.request_approval.assert_called_once()
    mock_apps.close_app.assert_called_once_with("notepad", force=False)
    calls = mock_client.update_task.call_args_list
    assert calls[-1].kwargs["status"] == TaskStatus.COMPLETED

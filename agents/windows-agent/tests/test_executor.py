from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import pytest
from contracts.approvals.models import ApprovalResponse, ApprovalStatus
from contracts.tasks.models import TaskPriority, TaskResponse, TaskStatus, TaskTargetDevice
from windows_agent.executor import TaskExecutor
from windows_agent.tools.file_tools import FileTools


class FakeTaskClient:
    def __init__(self, should_approve: bool = True) -> None:
        self.should_approve = should_approve
        self.task_updates: List[Dict] = []
        self.approvals_requested: List[Dict] = []

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        result_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.task_updates.append({
            "task_id": task_id,
            "status": status,
            "result_summary": result_summary,
            "error_message": error_message,
            "result_data": result_data,
        })

    def request_approval(self, task_id: str, action_type: str, description: str, details: dict = None) -> ApprovalResponse:
        self.approvals_requested.append({
            "task_id": task_id,
            "action_type": action_type,
            "description": description,
        })
        return ApprovalResponse(
            id="appr-123",
            task_id=task_id,
            action_type=action_type,
            description=description,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )

    def poll_approval(self, approval_id: str, timeout_seconds: float = 60.0) -> ApprovalResponse:
        status = ApprovalStatus.APPROVED if self.should_approve else ApprovalStatus.REJECTED
        return ApprovalResponse(
            id=approval_id,
            task_id="t-1",
            action_type="file_move",
            description="desc",
            status=status,
            created_at=datetime.now(timezone.utc),
            rejection_reason="User denied action" if not self.should_approve else None,
        )


@pytest.fixture
def sandbox_env(tmp_path):
    tools = FileTools(allowed_roots=[tmp_path.resolve()])
    return tmp_path, tools


def test_executor_read_only_task(sandbox_env):
    tmp_path, tools = sandbox_env
    (tmp_path / "notes.txt").write_text("content")

    fake_client = FakeTaskClient()
    executor = TaskExecutor(client=fake_client, tools=tools)

    task = TaskResponse(
        id="task-1",
        title="List files",
        status=TaskStatus.PENDING,
        priority=TaskPriority.NORMAL,
        target_device=TaskTargetDevice.WINDOWS,
        payload={"action": "list_directory", "directory_path": str(tmp_path)},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    executor.execute(task)

    # Verify no approvals were needed for read-only operation
    assert len(fake_client.approvals_requested) == 0

    # Verify completed
    final_update = fake_client.task_updates[-1]
    assert final_update["status"] == TaskStatus.COMPLETED
    assert "1 item" in final_update["result_summary"]


def test_executor_move_file_approved(sandbox_env):
    tmp_path, tools = sandbox_env
    src = tmp_path / "source.txt"
    src.write_text("move me")
    dest_dir = tmp_path / "archive"
    dest_dir.mkdir()

    fake_client = FakeTaskClient(should_approve=True)
    executor = TaskExecutor(client=fake_client, tools=tools)

    task = TaskResponse(
        id="task-2",
        title="Move source.txt to archive",
        status=TaskStatus.PENDING,
        priority=TaskPriority.NORMAL,
        target_device=TaskTargetDevice.WINDOWS,
        payload={
            "action": "move_file",
            "source_path": str(src),
            "destination_path": str(dest_dir),
            "require_approval": True,
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    executor.execute(task)

    # Approval requested
    assert len(fake_client.approvals_requested) == 1
    assert fake_client.approvals_requested[0]["action_type"] == "file_move"

    # Execution succeeded
    assert not src.exists()
    assert (dest_dir / "source.txt").exists()
    assert fake_client.task_updates[-1]["status"] == TaskStatus.COMPLETED


def test_executor_move_file_rejected(sandbox_env):
    tmp_path, tools = sandbox_env
    src = tmp_path / "critical.txt"
    src.write_text("do not move")
    dest_dir = tmp_path / "somewhere"
    dest_dir.mkdir()

    fake_client = FakeTaskClient(should_approve=False)  # User clicks Reject
    executor = TaskExecutor(client=fake_client, tools=tools)

    task = TaskResponse(
        id="task-3",
        title="Move critical.txt",
        status=TaskStatus.PENDING,
        priority=TaskPriority.NORMAL,
        target_device=TaskTargetDevice.WINDOWS,
        payload={
            "action": "move_file",
            "source_path": str(src),
            "destination_path": str(dest_dir),
            "require_approval": True,
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    executor.execute(task)

    # Approval requested
    assert len(fake_client.approvals_requested) == 1

    # File NOT moved because user rejected
    assert src.exists()
    assert not (dest_dir / "critical.txt").exists()

    # Task marked as failed due to rejection
    final_update = fake_client.task_updates[-1]
    assert final_update["status"] == TaskStatus.FAILED
    assert "rejected" in final_update["error_message"].lower()

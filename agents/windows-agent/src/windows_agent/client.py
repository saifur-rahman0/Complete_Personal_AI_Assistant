import time
from typing import Any, Dict, List, Optional
import httpx
from contracts.approvals.models import ApprovalResponse, ApprovalStatus
from contracts.tasks.models import TaskResponse, TaskStatus, TaskUpdateRequest
from windows_agent.config import settings


class TaskServiceClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or settings.TASK_SERVICE_URL).rstrip("/")

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
    ) -> List[TaskResponse]:
        """Fetches tasks from task-service, optionally filtered by status."""
        params = {}
        if status:
            params["status"] = status.value

        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            resp = client.get("/api/v1/tasks", params=params)
            resp.raise_for_status()
            data = resp.json()
            return [TaskResponse(**item) for item in data.get("items", [])]

    def get_task(self, task_id: str) -> Optional[TaskResponse]:
        """Gets a single task by ID."""
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            resp = client.get(f"/api/v1/tasks/{task_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return TaskResponse(**resp.json())

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        result_summary: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> TaskResponse:
        """Updates task state or results."""
        payload = TaskUpdateRequest(
            status=status,
            result_summary=result_summary,
            result_data=result_data,
            error_message=error_message,
        )
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            resp = client.patch(
                f"/api/v1/tasks/{task_id}",
                json=payload.model_dump(exclude_unset=True),
            )
            resp.raise_for_status()
            return TaskResponse(**resp.json())

    def request_approval(
        self,
        task_id: str,
        action_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> ApprovalResponse:
        """Requests human authorization for a consequential or destructive action."""
        body = {
            "task_id": task_id,
            "action_type": action_type,
            "description": description,
            "details": details or {},
        }
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            resp = client.post("/api/v1/approvals", json=body)
            resp.raise_for_status()
            return ApprovalResponse(**resp.json())

    def get_approval(self, approval_id: str) -> Optional[ApprovalResponse]:
        """Gets current approval status."""
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            resp = client.get(f"/api/v1/approvals/{approval_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return ApprovalResponse(**resp.json())

    def poll_approval(
        self,
        approval_id: str,
        timeout_seconds: float = 60.0,
        interval_seconds: float = 1.0,
    ) -> ApprovalResponse:
        """Polls until approval is resolved (Approved or Rejected) or times out."""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            approval = self.get_approval(approval_id)
            if approval and approval.status != ApprovalStatus.PENDING:
                return approval
            time.sleep(interval_seconds)

        # Timed out without decision
        approval = self.get_approval(approval_id)
        if approval:
            return approval
        raise TimeoutError(f"Approval '{approval_id}' timed out after {timeout_seconds}s")


task_client = TaskServiceClient()

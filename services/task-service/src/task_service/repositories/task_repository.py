from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4
from contracts.tasks.models import TaskCreateRequest, TaskResponse, TaskStatus, TaskUpdateRequest
from contracts.approvals.models import ApprovalResponse, ApprovalStatus


class InMemoryTaskRepository:
    """Thread-safe in-memory task repository suitable for development and initial integration."""

    def __init__(self) -> None:
        self._tasks: Dict[str, TaskResponse] = {}
        self._approvals: Dict[str, ApprovalResponse] = {}

    def create_task(self, req: TaskCreateRequest) -> TaskResponse:
        now = datetime.now(timezone.utc)
        task_id = str(uuid4())
        task = TaskResponse(
            id=task_id,
            title=req.title,
            description=req.description,
            status=TaskStatus.PENDING,
            priority=req.priority,
            target_device=req.target_device,
            payload=req.payload,
            created_at=now,
            updated_at=now,
        )
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[TaskResponse]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[TaskResponse]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def update_task(self, task_id: str, req: TaskUpdateRequest) -> Optional[TaskResponse]:
        task = self._tasks.get(task_id)
        if not task:
            return None

        update_data = req.model_dump(exclude_unset=True)
        new_task = task.model_copy(update={
            **update_data,
            "updated_at": datetime.now(timezone.utc),
        })
        self._tasks[task_id] = new_task
        return new_task

    def create_approval(
        self,
        task_id: str,
        action_type: str,
        description: str,
        details: Optional[Dict] = None,
    ) -> ApprovalResponse:
        now = datetime.now(timezone.utc)
        approval_id = str(uuid4())
        approval = ApprovalResponse(
            id=approval_id,
            task_id=task_id,
            action_type=action_type,
            description=description,
            details=details or {},
            status=ApprovalStatus.PENDING,
            created_at=now,
        )
        self._approvals[approval_id] = approval
        return approval

    def get_approval(self, approval_id: str) -> Optional[ApprovalResponse]:
        return self._approvals.get(approval_id)

    def list_approvals(self, status: Optional[ApprovalStatus] = None) -> List[ApprovalResponse]:
        approvals = list(self._approvals.values())
        if status:
            approvals = [a for a in approvals if a.status == status]
        return sorted(approvals, key=lambda a: a.created_at, reverse=True)

    def resolve_approval(
        self,
        approval_id: str,
        approved: bool,
        reason: Optional[str] = None,
    ) -> Optional[ApprovalResponse]:
        approval = self._approvals.get(approval_id)
        if not approval:
            return None

        new_status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        resolved = approval.model_copy(update={
            "status": new_status,
            "resolved_at": datetime.now(timezone.utc),
            "rejection_reason": reason if not approved else None,
        })
        self._approvals[approval_id] = resolved
        return resolved


# Global repository instance
task_repository = InMemoryTaskRepository()

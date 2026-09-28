from typing import List, Optional
from contracts.tasks.models import (
    TaskCreateRequest,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
    TaskUpdateRequest,
)
from contracts.approvals.models import (
    ApprovalResolveRequest,
    ApprovalResponse,
    ApprovalStatus,
)
from task_service.repositories.task_repository import task_repository


class TaskService:
    def create_task(self, req: TaskCreateRequest) -> TaskResponse:
        return task_repository.create_task(req)

    def get_task(self, task_id: str) -> Optional[TaskResponse]:
        return task_repository.get_task(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> TaskListResponse:
        items = task_repository.list_tasks(status=status)
        return TaskListResponse(items=items, total=len(items))

    def update_task(self, task_id: str, req: TaskUpdateRequest) -> Optional[TaskResponse]:
        return task_repository.update_task(task_id, req)

    def create_approval(
        self,
        task_id: str,
        action_type: str,
        description: str,
        details: Optional[dict] = None,
    ) -> ApprovalResponse:
        approval = task_repository.create_approval(task_id, action_type, description, details)
        # Update task state to AWAITING_APPROVAL
        task_repository.update_task(
            task_id,
            TaskUpdateRequest(status=TaskStatus.AWAITING_APPROVAL),
        )
        return approval

    def get_approval(self, approval_id: str) -> Optional[ApprovalResponse]:
        return task_repository.get_approval(approval_id)

    def list_approvals(self, status: Optional[ApprovalStatus] = None) -> List[ApprovalResponse]:
        return task_repository.list_approvals(status=status)

    def resolve_approval(self, approval_id: str, req: ApprovalResolveRequest) -> Optional[ApprovalResponse]:
        approval = task_repository.resolve_approval(approval_id, req.approved, req.reason)
        if approval:
            # If approved, move task back to RUNNING or PENDING
            new_status = TaskStatus.RUNNING if req.approved else TaskStatus.FAILED
            task_repository.update_task(
                approval.task_id,
                TaskUpdateRequest(
                    status=new_status,
                    error_message=f"Action rejected by user: {req.reason}" if not req.approved else None,
                ),
            )
        return approval


task_service = TaskService()

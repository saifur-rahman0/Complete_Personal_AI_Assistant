from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from contracts.tasks.models import TaskPriority, TaskStatus, TaskTargetDevice


class TaskCreatedPayload(BaseModel):
    task_id: str = Field(..., description="ID of newly created task")
    title: str = Field(...)
    description: Optional[str] = None
    target_device: TaskTargetDevice = Field(...)
    priority: TaskPriority = Field(...)
    payload: Dict[str, Any] = Field(default_factory=dict)


class TaskStatusChangedPayload(BaseModel):
    task_id: str = Field(..., description="ID of task whose status changed")
    old_status: TaskStatus = Field(...)
    new_status: TaskStatus = Field(...)
    changed_at: datetime = Field(...)
    reason: Optional[str] = None

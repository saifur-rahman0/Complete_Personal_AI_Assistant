from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskTargetDevice(str, Enum):
    WINDOWS = "windows"
    ANDROID = "android"
    ANY = "any"


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Short human-readable summary of the task")
    description: Optional[str] = Field(default=None, description="Detailed instruction or user prompt")
    target_device: TaskTargetDevice = Field(default=TaskTargetDevice.WINDOWS, description="Target device for execution")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task execution priority")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Structured task parameters or context")


class TaskUpdateRequest(BaseModel):
    status: Optional[TaskStatus] = Field(default=None, description="Updated status")
    result_summary: Optional[str] = Field(default=None, description="Execution outcome summary")
    error_message: Optional[str] = Field(default=None, description="Error details if task failed")


class TaskResponse(BaseModel):
    id: str = Field(..., description="Unique task UUID")
    title: str = Field(...)
    description: Optional[str] = None
    status: TaskStatus = Field(...)
    priority: TaskPriority = Field(...)
    target_device: TaskTargetDevice = Field(...)
    payload: Dict[str, Any] = Field(default_factory=dict)
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)


class TaskListResponse(BaseModel):
    items: List[TaskResponse] = Field(default_factory=list)
    total: int = Field(..., ge=0)

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReminderStatus(str, Enum):
    PENDING = "pending"
    DUE = "due"
    DELIVERED = "delivered"
    DISMISSED = "dismissed"
    CANCELLED = "cancelled"


class ReminderTargetDevice(str, Enum):
    ANDROID = "android"
    WINDOWS = "windows"
    ANY = "any"


class ReminderCreateRequest(BaseModel):
    title: str = Field(..., description="Short title of the reminder", min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, description="Optional extra details")
    trigger_at: datetime = Field(..., description="Timestamp when the reminder should trigger")
    cron_expression: Optional[str] = Field(default=None, description="Standard cron expression for recurring reminders")
    target_device: ReminderTargetDevice = Field(default=ReminderTargetDevice.ANY, description="Destination device")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata or payload")


class ReminderResponse(BaseModel):
    id: str = Field(..., description="Unique reminder ID")
    title: str
    description: Optional[str] = None
    trigger_at: datetime
    cron_expression: Optional[str] = None
    status: ReminderStatus = ReminderStatus.PENDING
    target_device: ReminderTargetDevice = ReminderTargetDevice.ANY
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReminderListResponse(BaseModel):
    items: List[ReminderResponse]
    total: int

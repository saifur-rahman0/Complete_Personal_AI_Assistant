from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from contracts.approvals.models import ApprovalStatus


class ApprovalRequestedPayload(BaseModel):
    approval_id: str = Field(...)
    task_id: str = Field(...)
    action_type: str = Field(...)
    description: str = Field(...)
    details: Dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(...)


class ApprovalResolvedPayload(BaseModel):
    approval_id: str = Field(...)
    task_id: str = Field(...)
    status: ApprovalStatus = Field(...)
    resolved_at: datetime = Field(...)
    reason: Optional[str] = None

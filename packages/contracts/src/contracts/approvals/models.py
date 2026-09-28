from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalResponse(BaseModel):
    id: str = Field(..., description="Unique approval request UUID")
    task_id: str = Field(..., description="Associated task UUID")
    action_type: str = Field(..., description="Action category, e.g. file_delete, file_move, system_command")
    description: str = Field(..., description="Clear explanation of the action needing confirmation")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed context such as affected file paths")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    created_at: datetime = Field(...)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    rejection_reason: Optional[str] = None


class ApprovalResolveRequest(BaseModel):
    approved: bool = Field(..., description="True if human approved, False if rejected")
    reason: Optional[str] = Field(default=None, description="Optional explanation for approval or rejection")

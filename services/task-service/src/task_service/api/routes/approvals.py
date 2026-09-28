from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from contracts.approvals.models import (
    ApprovalResolveRequest,
    ApprovalResponse,
    ApprovalStatus,
)
from task_service.schemas.errors import ErrorResponse
from task_service.services.task_service import task_service

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


class ApprovalCreatePayload(BaseModel):
    task_id: str = Field(...)
    action_type: str = Field(...)
    description: str = Field(...)
    details: Optional[dict] = Field(default_factory=dict)


@router.post(
    "",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new human authorization request",
)
def create_approval(payload: ApprovalCreatePayload) -> ApprovalResponse:
    task = task_service.get_task(payload.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{payload.task_id}' not found",
        )
    return task_service.create_approval(
        task_id=payload.task_id,
        action_type=payload.action_type,
        description=payload.description,
        details=payload.details,
    )


@router.get(
    "",
    response_model=List[ApprovalResponse],
    summary="List approvals (used by Android companion app)",
)
def list_approvals(status: Optional[ApprovalStatus] = Query(default=None)) -> List[ApprovalResponse]:
    return task_service.list_approvals(status=status)


@router.get(
    "/{approval_id}",
    response_model=ApprovalResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get approval details by ID",
)
def get_approval(approval_id: str) -> ApprovalResponse:
    approval = task_service.get_approval(approval_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval '{approval_id}' not found",
        )
    return approval


@router.post(
    "/{approval_id}/resolve",
    response_model=ApprovalResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Resolve an approval (Approve or Reject via Android/desktop)",
)
def resolve_approval(approval_id: str, req: ApprovalResolveRequest) -> ApprovalResponse:
    approval = task_service.resolve_approval(approval_id, req)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval '{approval_id}' not found",
        )
    return approval

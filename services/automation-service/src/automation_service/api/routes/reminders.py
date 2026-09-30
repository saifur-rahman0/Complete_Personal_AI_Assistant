from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from contracts.reminders.models import (
    ReminderCreateRequest,
    ReminderListResponse,
    ReminderResponse,
    ReminderStatus,
)
from automation_service.domain.scheduler import reminder_scheduler
from automation_service.repository.in_memory import reminder_repo

router = APIRouter(prefix="/api/v1/reminders", tags=["reminders"])


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a new reminder",
)
def create_reminder(req: ReminderCreateRequest) -> ReminderResponse:
    return reminder_scheduler.create_reminder(req)


@router.get(
    "",
    response_model=ReminderListResponse,
    summary="List all reminders",
)
def list_reminders(
    status: Optional[ReminderStatus] = Query(default=None, description="Filter by status"),
) -> ReminderListResponse:
    items = reminder_repo.list(status=status)
    return ReminderListResponse(items=items, total=len(items))


@router.get(
    "/due",
    response_model=List[ReminderResponse],
    summary="Get and update currently due reminders",
)
def get_due_reminders() -> List[ReminderResponse]:
    return reminder_scheduler.check_due_reminders()


@router.get(
    "/{reminder_id}",
    response_model=ReminderResponse,
    summary="Get reminder details",
)
def get_reminder(reminder_id: str) -> ReminderResponse:
    item = reminder_repo.get(reminder_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reminder '{reminder_id}' not found")
    return item


@router.post(
    "/{reminder_id}/dismiss",
    response_model=ReminderResponse,
    summary="Acknowledge / dismiss a due reminder",
)
def dismiss_reminder(reminder_id: str) -> ReminderResponse:
    item = reminder_scheduler.dismiss_reminder(reminder_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reminder '{reminder_id}' not found")
    return item


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel a scheduled reminder",
)
def cancel_reminder(reminder_id: str) -> None:
    success = reminder_scheduler.cancel_reminder(reminder_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reminder '{reminder_id}' not found")

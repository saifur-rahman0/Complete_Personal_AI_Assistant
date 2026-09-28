from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from contracts.tasks.models import (
    TaskCreateRequest,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
    TaskUpdateRequest,
)
from task_service.schemas.errors import ErrorResponse
from task_service.services.task_service import task_service

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_task(req: TaskCreateRequest) -> TaskResponse:
    return task_service.create_task(req)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List all tasks with optional status filter",
)
def list_tasks(status: Optional[TaskStatus] = Query(default=None)) -> TaskListResponse:
    return task_service.list_tasks(status=status)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get task by ID",
)
def get_task(task_id: str) -> TaskResponse:
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Update task status or outcomes",
)
def update_task(task_id: str, req: TaskUpdateRequest) -> TaskResponse:
    task = task_service.update_task(task_id, req)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )
    return task

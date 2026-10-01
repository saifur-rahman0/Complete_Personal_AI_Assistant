import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request, Response, status
import httpx
from contracts.gateway.models import GatewayEventType
from gateway.audit import audit_logger
from gateway.chat_store import chat_store
from gateway.config import settings
from gateway.sync import sync_engine

logger = logging.getLogger("gateway.api.tasks")
router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.get("/tasks", summary="List tasks from task-service")
async def list_tasks(request: Request):
    try:
        async with httpx.AsyncClient(base_url=settings.TASK_SERVICE_URL, timeout=8.0) as client:
            resp = await client.get("/api/v1/tasks", params=dict(request.query_params))
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for t in items:
                if t.get("status") == "completed" and t.get("result_summary"):
                    chat_store.update_task_message(t.get("id", ""), t["result_summary"])
            return data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/tasks/{task_id}", summary="Get task by ID")
async def get_task(task_id: str):
    try:
        async with httpx.AsyncClient(base_url=settings.TASK_SERVICE_URL, timeout=5.0) as client:
            resp = await client.get(f"/api/v1/tasks/{task_id}")
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "completed" and data.get("result_summary"):
                chat_store.update_task_message(data.get("id", ""), data["result_summary"])
            return data
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/approvals", summary="List approval requests")
async def list_approvals(request: Request):
    try:
        async with httpx.AsyncClient(base_url=settings.TASK_SERVICE_URL, timeout=8.0) as client:
            resp = await client.get("/api/v1/approvals", params=dict(request.query_params))
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/approvals/{approval_id}/resolve", summary="Resolve pending human approval request")
async def resolve_approval(approval_id: str, request: Request):
    body = await request.json()
    try:
        async with httpx.AsyncClient(base_url=settings.TASK_SERVICE_URL, timeout=8.0) as client:
            resp = await client.post(f"/api/v1/approvals/{approval_id}/resolve", json=body)
            resp.raise_for_status()
            data = resp.json()

            # Record event in sync journal and stream
            sync_engine.record_event(
                event_type=GatewayEventType.APPROVAL_RESOLVED,
                payload={"approval_id": approval_id, "resolution": data},
            )

            # Record security audit log
            approved = body.get("approved", True)
            audit_logger.record(
                action="resolve_approval",
                actor=request.headers.get("X-Device-Id") or "unknown",
                target=f"approval:{approval_id}",
                status="SUCCESS" if approved else "REJECTED",
                correlation_id=request.headers.get("X-Correlation-ID"),
                details=body,
            )

            return data
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

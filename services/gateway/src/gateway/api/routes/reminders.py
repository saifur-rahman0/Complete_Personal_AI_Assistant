import logging
from fastapi import APIRouter, HTTPException, Request, status
import httpx
from gateway.config import settings

logger = logging.getLogger("gateway.api.reminders")
router = APIRouter(prefix="/api/v1/reminders", tags=["reminders"])


@router.get("", summary="List reminders")
async def list_reminders(request: Request):
    try:
        async with httpx.AsyncClient(base_url=settings.AUTOMATION_SERVICE_URL, timeout=5.0) as client:
            resp = await client.get("/api/v1/reminders", params=dict(request.query_params))
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("", summary="Schedule reminder")
async def create_reminder(request: Request):
    body = await request.json()
    try:
        async with httpx.AsyncClient(base_url=settings.AUTOMATION_SERVICE_URL, timeout=5.0) as client:
            resp = await client.post("/api/v1/reminders", json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/due", summary="List due reminders")
async def list_due_reminders():
    try:
        async with httpx.AsyncClient(base_url=settings.AUTOMATION_SERVICE_URL, timeout=5.0) as client:
            resp = await client.get("/api/v1/reminders/due")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/{reminder_id}/dismiss", summary="Dismiss due reminder")
async def dismiss_reminder(reminder_id: str):
    try:
        async with httpx.AsyncClient(base_url=settings.AUTOMATION_SERVICE_URL, timeout=5.0) as client:
            resp = await client.post(f"/api/v1/reminders/{reminder_id}/dismiss", json={})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

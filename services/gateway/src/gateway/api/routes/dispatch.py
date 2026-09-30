import logging
from typing import Any, Dict
from fastapi import APIRouter, Header, HTTPException, Request, status
import httpx
from contracts.gateway.models import GatewayEventType
from gateway.config import settings
from gateway.sync import sync_engine

logger = logging.getLogger("gateway.api.dispatch")
router = APIRouter(prefix="/api/v1", tags=["dispatch"])


@router.post("/dispatch", summary="Forward user prompt to Decision Router and stream event")
async def dispatch_prompt(
    request: Request,
    x_correlation_id: str = Header(default=""),
    x_device_id: str = Header(default="unknown"),
):
    body = await request.json()
    headers = {"X-Correlation-ID": x_correlation_id, "X-Device-Id": x_device_id}

    try:
        async with httpx.AsyncClient(base_url=settings.ROUTER_SERVICE_URL, timeout=15.0) as client:
            resp = await client.post("/api/v1/router/dispatch", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            # Record event in sync engine journal and broadcast
            task = data.get("task")
            if task:
                sync_engine.record_event(
                    event_type=GatewayEventType.TASK_CREATED,
                    payload={"task": task, "decision": data.get("decision")},
                    device_id=x_device_id,
                    correlation_id=x_correlation_id,
                )

            return data
    except Exception as e:
        logger.error(f"Error dispatching to router: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Downstream decision-router error: {str(e)}",
        )

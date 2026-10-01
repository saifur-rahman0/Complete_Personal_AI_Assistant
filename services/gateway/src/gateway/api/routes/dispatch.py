import logging
from typing import Any, Dict
from fastapi import APIRouter, Header, HTTPException, Request, status
import httpx
from contracts.gateway.models import GatewayEventType
from gateway.chat_store import chat_store
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
    prompt = body.get("prompt", "")
    headers = {"X-Correlation-ID": x_correlation_id, "X-Device-Id": x_device_id}

    # Record user message to synchronized chat history
    if prompt:
        chat_store.add_message(role="user", text=prompt, device=x_device_id)

    # Attach recent conversation history (excluding the prompt just added)
    all_msgs = chat_store.get_messages(limit=10)
    body["history"] = [
        {"role": m["role"], "text": m["text"]}
        for m in (all_msgs[:-1] if prompt else all_msgs)
    ]

    try:
        async with httpx.AsyncClient(base_url=settings.ROUTER_SERVICE_URL, timeout=15.0) as client:
            resp = await client.post("/api/v1/router/dispatch", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            # Record assistant reply to synchronized chat history
            reply = data.get("message")
            if reply:
                chat_store.add_message(role="assistant", text=reply, device="assistant")

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
        fallback_msg = (
            "I'm having trouble reaching the decision router service. "
            "Please ensure all backend microservices are running via 'scripts/run_local.py'."
        )
        chat_store.add_message(role="assistant", text=fallback_msg, device="assistant")
        return {
            "decision": {
                "intent": "general_query",
                "confidence": 0.0,
                "target_service": "none",
                "requires_deep_reasoning": False,
                "structured_action": None,
                "structured_payload": {},
                "latency_ms": 0.0,
            },
            "task": None,
            "message": fallback_msg,
        }

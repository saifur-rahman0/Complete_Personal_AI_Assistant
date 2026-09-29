import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
import httpx
from pydantic import BaseModel, Field
from contracts.router.models import IntentType, RouteDecision, RouteRequest
from contracts.tasks.models import TaskCreateRequest, TaskResponse, TaskTargetDevice
from decision_router.classifiers.llm_extractor import llm_extractor
from decision_router.classifiers.system_one import system_one_classifier
from decision_router.config import settings

logger = logging.getLogger("decision_router.api")
router = APIRouter(prefix="/api/v1/router", tags=["router"])


class DispatchResponse(BaseModel):
    decision: RouteDecision
    task: Optional[TaskResponse] = Field(default=None, description="Created task if dispatched")
    message: str


@router.post(
    "/classify",
    response_model=RouteDecision,
    summary="Classify user prompt into intent and structured tool call",
)
def classify_prompt(req: RouteRequest) -> RouteDecision:
    # 1. Fast System One decision
    decision = system_one_classifier.classify(req)

    # 2. If System One requires deep reasoning or has low confidence, try LLM extraction
    if decision.requires_deep_reasoning or decision.confidence < settings.CONFIDENCE_THRESHOLD:
        llm_params = llm_extractor.extract_file_parameters(req.prompt)
        if llm_params and "action" in llm_params:
            decision.intent = IntentType.FILE_MANAGEMENT
            decision.confidence = 0.95
            decision.target_service = "windows-agent"
            decision.structured_action = llm_params["action"]
            decision.structured_payload = llm_params

    return decision


@router.post(
    "/dispatch",
    response_model=DispatchResponse,
    summary="Classify prompt and automatically create task in task-service",
)
def dispatch_prompt(req: RouteRequest) -> DispatchResponse:
    decision = classify_prompt(req)

    # If it is a file management action for the Windows agent, create the task
    if decision.intent == IntentType.FILE_MANAGEMENT and decision.structured_action:
        task_payload = {
            "action": decision.structured_action,
            **decision.structured_payload,
        }

        task_create = TaskCreateRequest(
            title=f"File Action: {decision.structured_action.replace('_', ' ').title()}",
            description=req.prompt,
            target_device=TaskTargetDevice.WINDOWS,
            payload=task_payload,
        )

        try:
            with httpx.Client(base_url=settings.TASK_SERVICE_URL, timeout=5.0) as client:
                resp = client.post("/api/v1/tasks", json=task_create.model_dump())
                resp.raise_for_status()
                created_task = TaskResponse(**resp.json())

                return DispatchResponse(
                    decision=decision,
                    task=created_task,
                    message=f"Dispatched task '{created_task.title}' to Windows Agent (Task ID: {created_task.id})",
                )
        except Exception as e:
            logger.warning(f"Could not forward to task-service: {e}")
            return DispatchResponse(
                decision=decision,
                task=None,
                message=f"Classified successfully, but task-service is unreachable: {e}",
            )

    return DispatchResponse(
        decision=decision,
        task=None,
        message=f"Prompt classified as '{decision.intent.value}'. No automated task created.",
    )

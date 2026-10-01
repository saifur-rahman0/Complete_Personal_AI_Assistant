import logging
import re
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
import httpx
from pydantic import BaseModel, Field
from contracts.router.models import IntentType, RouteDecision, RouteRequest
from contracts.tasks.models import TaskCreateRequest, TaskResponse, TaskTargetDevice
from decision_router.classifiers.laya_classifier import neural_laya_classifier
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
def classify_prompt(req: RouteRequest, use_neural: Optional[bool] = None) -> RouteDecision:
    # 1. Neural Laya or Fast Heuristic System One decision
    active_use_neural = use_neural if use_neural is not None else settings.USE_NEURAL_LAYA
    if active_use_neural and neural_laya_classifier.is_available():
        decision = neural_laya_classifier.classify(req)
    else:
        decision = system_one_classifier.classify(req)

    # 2. If System One requires deep reasoning or has low confidence, try LLM extraction for file candidates
    is_file_candidate = (
        decision.intent == IntentType.FILE_MANAGEMENT
        or any(w in req.prompt.lower() for w in ["file", "folder", "directory", "download", "document", "desktop", "pdf", "organize", "sort", "move", "clean"])
    )
    if is_file_candidate and (decision.requires_deep_reasoning or decision.confidence < settings.CONFIDENCE_THRESHOLD):
        llm_params = llm_extractor.extract_file_parameters(req.prompt)
        if llm_params and "action" in llm_params:
            decision.intent = IntentType.FILE_MANAGEMENT
            decision.confidence = 0.95
            decision.target_service = "windows-agent"
            decision.structured_action = llm_params["action"]
            decision.structured_payload = llm_params

    return decision


def _format_conversational_response(prompt: str) -> str:
    # 1. Try local Ollama LLM if reachable
    llm_reply = llm_extractor.generate_chat_response(prompt)
    if llm_reply:
        return llm_reply

    # 2. Smart fallback if Ollama is still downloading or offline
    lower = prompt.strip().lower()

    # Greetings
    if re.search(r"^(hi|hello|hey|greetings|howdy|good\s+(morning|afternoon|evening))\b", lower):
        return (
            "Hello! I am Jarvis, your personal AI assistant. How can I help you today? "
            "You can ask me to organize files, check system status, launch apps, set reminders, or research topics."
        )

    # Capabilities / Who are you
    if any(q in lower for q in ["who are you", "what can you do", "help", "capabilities", "what are you"]):
        return (
            "I am Jarvis, your cross-device personal AI assistant. Here is what I can do:\n"
            "• File & Folder Management (organizing, searching, moving files)\n"
            "• Desktop Automation (monitoring CPU/battery, launching/closing apps)\n"
            "• Scheduled Reminders & Contextual Memory\n"
            "• SSRF-Safe Web Research\n"
            "Try a command like 'Organize Downloads' or 'Show system telemetry'!"
        )

    # Thank you / appreciation
    if re.search(r"\b(thank|thanks|great job|awesome|good job)\b", lower):
        return "You're very welcome! Let me know if you need anything else."

    # Status inquiry
    if "how are you" in lower:
        return "I'm running smoothly and ready for tasks! How can I assist you on your workstation today?"

    # General conversational fallback
    return (
        f"I received your message: \"{prompt}\". "
        "For automated actions, try giving me a command like 'Organize Downloads', 'Show system telemetry', "
        "or 'Remind me in 10 minutes'."
    )


@router.post(
    "/dispatch",
    response_model=DispatchResponse,
    summary="Classify prompt and automatically create task in task-service",
)
def dispatch_prompt(req: RouteRequest) -> DispatchResponse:
    try:
        decision = classify_prompt(req)
    except Exception as e:
        logger.warning(f"Classification encountered an error ({e}); gracefully falling back to System One.")
        decision = system_one_classifier.classify(req)

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

    # If it is a reminder, dispatch to automation-service
    if decision.intent == IntentType.REMINDER:
        reminder_payload = decision.structured_payload or {}
        reminder_create = {
            "title": reminder_payload.get("title", req.prompt),
            "description": req.prompt,
            "trigger_at": reminder_payload.get("trigger_at"),
            "target_device": "any",
        }

        try:
            with httpx.Client(base_url=settings.AUTOMATION_SERVICE_URL, timeout=5.0) as client:
                resp = client.post("/api/v1/reminders", json=reminder_create)
                resp.raise_for_status()
                data = resp.json()
                return DispatchResponse(
                    decision=decision,
                    task=None,
                    message=f"Scheduled reminder: '{data['title']}' (triggers at {data['trigger_at']})",
                )
        except Exception as e:
            logger.warning(f"Could not forward to automation-service: {e}")
            return DispatchResponse(
                decision=decision,
                task=None,
                message=f"Reminder classified, but automation-service is unreachable: {e}",
            )

    # If it is a web research request, dispatch to web-research service
    if decision.intent == IntentType.WEB_RESEARCH:
        research_query = decision.structured_payload.get("query", req.prompt)
        try:
            with httpx.Client(base_url=settings.WEB_RESEARCH_SERVICE_URL, timeout=15.0) as client:
                resp = client.post("/api/v1/research/search", json={"query": research_query, "max_sources": 3})
                resp.raise_for_status()
                data = resp.json()
                return DispatchResponse(
                    decision=decision,
                    task=None,
                    message=f"Web Research: {data['summary']}",
                )
        except Exception as e:
            logger.warning(f"Could not forward to web-research: {e}")
            return DispatchResponse(
                decision=decision,
                task=None,
                message=f"Web research classified, but web-research service is unreachable: {e}",
            )

    # If it is desktop automation, dispatch task to Windows Agent via task-service
    if decision.intent == IntentType.DESKTOP_AUTOMATION and decision.structured_action:
        task_payload = {
            "action": decision.structured_action,
            **decision.structured_payload,
        }

        task_create = TaskCreateRequest(
            title=f"Desktop Action: {decision.structured_action.replace('_', ' ').title()}",
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
                    message=f"Dispatched desktop task '{created_task.title}' to Windows Agent (Task ID: {created_task.id})",
                )
        except Exception as e:
            logger.warning(f"Could not forward to task-service: {e}")
            return DispatchResponse(
                decision=decision,
                task=None,
                message=f"Desktop action classified, but task-service is unreachable: {e}",
            )

    if decision.intent == IntentType.GENERAL_QUERY:
        conversational_reply = _format_conversational_response(req.prompt)
        return DispatchResponse(
            decision=decision,
            task=None,
            message=conversational_reply,
        )

    return DispatchResponse(
        decision=decision,
        task=None,
        message=f"Prompt classified as '{decision.intent.value}'. No automated task created.",
    )


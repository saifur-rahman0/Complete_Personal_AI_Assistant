import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
import httpx
from pydantic import BaseModel, Field
from contracts.router.models import IntentType, RouteDecision, RouteRequest
from contracts.tasks.models import TaskCreateRequest, TaskResponse, TaskStatus, TaskTargetDevice
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
    prompt_lower = req.prompt.lower()
    has_file_history = any(
        ("file" in h.get("text", "").lower() or "[" in h.get("text", "") or "found" in h.get("text", "").lower())
        for h in req.history[-3:]
    ) if req.history else False

    is_file_candidate = (
        decision.intent == IntentType.FILE_MANAGEMENT
        or any(w in prompt_lower for w in [
            "file", "folder", "directory", "download", "document", "desktop", "pdf",
            "doc", "docx", "txt", "xlsx", "csv", "image", "photo", "video",
            "resume", "invoice", "receipt", "organize", "sort", "move", "clean", "find", "search"
        ])
        or (has_file_history and any(w in prompt_lower for w in [
            "open", "read", "view", "see", "show", "preview", "delete", "remove", "rename", "first", "second", "last", "it", "that", "which"
        ]))
    )
    if is_file_candidate and (decision.requires_deep_reasoning or decision.confidence < settings.CONFIDENCE_THRESHOLD):
        llm_params = llm_extractor.extract_file_parameters(req.prompt, history=req.history)
        if llm_params and "action" in llm_params:
            action = llm_params["action"]
            # Validate required file_path for single-file operations
            if action in ("read_file", "open_file", "rename_file", "delete_file") and not (llm_params.get("file_path") or llm_params.get("path")):
                pass
            else:
                if not llm_params.get("directory_path") and action in ("list_directory", "search_files", "organize_folder"):
                    llm_params["directory_path"] = str(Path.home() / "Downloads")
                decision.intent = IntentType.FILE_MANAGEMENT
                decision.confidence = 0.95
                decision.target_service = "windows-agent"
                decision.structured_action = action
                decision.structured_payload = llm_params

    return decision


def _format_conversational_response(prompt: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    # 1. Try local or cloud LLM with multi-turn conversation history
    llm_reply = llm_extractor.generate_chat_response(prompt, history=history)
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


def _wait_for_task_completion(task_id: str, timeout_seconds: float = 3.0) -> Optional[TaskResponse]:
    """Polls task-service briefly for fast-completing actions so the chat receives live results immediately."""
    start = time.time()
    try:
        with httpx.Client(base_url=settings.TASK_SERVICE_URL, timeout=timeout_seconds + 1.0) as client:
            while time.time() - start < timeout_seconds:
                time.sleep(0.15)
                resp = client.get(f"/api/v1/tasks/{task_id}")
                if resp.status_code == 200:
                    task = TaskResponse(**resp.json())
                    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.AWAITING_APPROVAL):
                        return task
    except Exception as e:
        logger.warning(f"Error while polling task completion for {task_id}: {e}")
    return None


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

                # Await quick task completion for instant results in chat
                completed = _wait_for_task_completion(created_task.id, timeout_seconds=3.0)
                if completed and completed.status == TaskStatus.COMPLETED:
                    return DispatchResponse(
                        decision=decision,
                        task=completed,
                        message=completed.result_summary or f"Task '{completed.title}' completed successfully.",
                    )
                elif completed and completed.status == TaskStatus.AWAITING_APPROVAL:
                    return DispatchResponse(
                        decision=decision,
                        task=completed,
                        message=f"Action '{created_task.title}' requires your authorization. Please check Pending Approvals.",
                    )
                elif completed and completed.status == TaskStatus.FAILED:
                    return DispatchResponse(
                        decision=decision,
                        task=completed,
                        message=f"Action failed: {completed.error_message or 'Unknown error'}",
                    )

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

                # Await quick task completion for instant telemetry/status results in chat
                completed = _wait_for_task_completion(created_task.id, timeout_seconds=3.0)
                if completed and completed.status == TaskStatus.COMPLETED:
                    return DispatchResponse(
                        decision=decision,
                        task=completed,
                        message=completed.result_summary or f"Action '{completed.title}' completed successfully.",
                    )
                elif completed and completed.status == TaskStatus.FAILED:
                    return DispatchResponse(
                        decision=decision,
                        task=completed,
                        message=f"Action failed: {completed.error_message or 'Unknown error'}",
                    )

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
        conversational_reply = _format_conversational_response(req.prompt, history=req.history)
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


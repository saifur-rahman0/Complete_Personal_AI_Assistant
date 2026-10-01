from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    FILE_MANAGEMENT = "file_management"
    REMINDER = "reminder"
    WEB_RESEARCH = "web_research"
    SYSTEM_AUTOMATION = "system_automation"
    DESKTOP_AUTOMATION = "desktop_automation"
    GENERAL_QUERY = "general_query"



class RouteRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Raw user prompt or command")
    device_context: str = Field(default="windows", description="Device initiating the request ('windows', 'android')")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent conversation turns for context")


class RouteDecision(BaseModel):
    intent: IntentType = Field(..., description="Classified intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence score")
    target_service: str = Field(..., description="Target service/agent for execution")
    requires_deep_reasoning: bool = Field(default=False, description="Whether LLM deep reasoning is needed")
    structured_action: Optional[str] = Field(default=None, description="Suggested action, e.g. organize_folder, move_file")
    structured_payload: Dict[str, Any] = Field(default_factory=dict, description="Extracted tool parameters")
    latency_ms: float = Field(default=0.0, description="Routing computation latency in milliseconds")

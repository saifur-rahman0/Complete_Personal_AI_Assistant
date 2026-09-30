from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GatewayEventType(str, Enum):
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_STATUS_CHANGED = "task.status_changed"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RESOLVED = "approval.resolved"
    REMINDER_DUE = "reminder.due"
    REMINDER_TRIGGERED = "reminder.triggered"
    TELEMETRY_UPDATED = "telemetry.updated"
    DEVICE_CONNECTED = "device.connected"
    DEVICE_DISCONNECTED = "device.disconnected"


class GatewaySyncEvent(BaseModel):
    event_id: str = Field(description="Unique monotonic or UUID event identifier")
    event_type: GatewayEventType = Field(description="Type of synchronization event")
    device_id: Optional[str] = Field(default=None, description="Device associated with event if applicable")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data payload")
    correlation_id: Optional[str] = Field(default=None, description="Distributed correlation tracking ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of event generation")


class OfflineActionItem(BaseModel):
    action_id: str = Field(description="Client-generated unique ID for idempotent replay")
    action_type: str = Field(description="Action name (e.g. resolve_approval, dispatch_prompt, dismiss_reminder)")
    payload: Dict[str, Any] = Field(default_factory=dict)
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncBatchRequest(BaseModel):
    client_device_id: str = Field(default="", description="Device requesting synchronization")
    device_id: Optional[str] = Field(default=None, description="Device requesting synchronization (alias)")
    last_event_id: Optional[str] = Field(default=None, description="Last known event ID seen by client")
    offline_actions: List[OfflineActionItem] = Field(default_factory=list, description="Actions queued locally while offline")

    def get_device_id(self) -> str:
        return self.device_id or self.client_device_id or "unknown"


class SyncBatchResponse(BaseModel):
    events: List[GatewaySyncEvent] = Field(default_factory=list, description="New events that occurred since last_event_id")
    processed_action_ids: List[str] = Field(default_factory=list, description="IDs of offline actions successfully applied")
    latest_event_id: Optional[str] = Field(default=None, description="Latest event ID in stream")
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

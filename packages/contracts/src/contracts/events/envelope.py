from datetime import datetime, timezone
from typing import Any, Dict, Generic, Optional, TypeVar
from uuid import uuid4
from pydantic import BaseModel, Field

T = TypeVar("T")


class EventEnvelope(BaseModel, Generic[T]):
    """Standardized asynchronous event envelope adhering to system architecture guidelines."""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event identifier")
    type: str = Field(..., description="Event type name in dot notation, e.g. task.created")
    version: str = Field(default="v1", description="Contract schema version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event creation timestamp in UTC"
    )
    producer: str = Field(..., description="Name of the producing service, e.g. task-service")
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Distributed tracing correlation ID"
    )
    payload: T = Field(..., description="Event payload data")

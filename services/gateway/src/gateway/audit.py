from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("gateway.audit")


class AuditLogEntry(BaseModel):
    audit_id: str = Field(description="Unique ID for this audit event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = Field(description="Device or IP that initiated the action")
    action: str = Field(description="Consequential or security action performed")
    target: Optional[str] = Field(default=None, description="Resource or entity targeted")
    status: str = Field(description="Action outcome: SUCCESS, REJECTED, FAILED, PENDING")
    correlation_id: Optional[str] = Field(default=None)
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    """
    Structured security and compliance audit journal.
    Maintains an in-memory ring buffer of audit logs and outputs structured JSON.
    """

    def __init__(self, max_entries: int = 500) -> None:
        self.max_entries = max_entries
        self._entries: List[AuditLogEntry] = []
        self._counter: int = 0

    def record(
        self,
        action: str,
        actor: str,
        status: str,
        target: Optional[str] = None,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLogEntry:
        self._counter += 1
        entry = AuditLogEntry(
            audit_id=f"audit_{self._counter:06d}",
            actor=actor,
            action=action,
            target=target,
            status=status,
            correlation_id=correlation_id,
            details=details or {},
        )

        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]

        # Structured machine-readable log line
        logger.info(
            f"[AUDIT] action={entry.action} actor={entry.actor} status={entry.status} "
            f"target={entry.target} corr_id={entry.correlation_id} "
            f"details={json.dumps(entry.details)}"
        )
        return entry

    def list_entries(self, limit: int = 50) -> List[AuditLogEntry]:
        return list(reversed(self._entries[-limit:]))


audit_logger = AuditLogger()

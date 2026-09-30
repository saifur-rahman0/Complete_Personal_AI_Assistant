from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import httpx
from contracts.gateway.models import (
    GatewayEventType,
    GatewaySyncEvent,
    OfflineActionItem,
    SyncBatchRequest,
    SyncBatchResponse,
)
from gateway.config import settings
from gateway.stream import connection_manager

logger = logging.getLogger("gateway.sync")


class SyncEngine:
    """
    Maintains a reliable in-memory append-only event journal and reconciles
    actions dispatched by companion clients while temporarily offline.
    """

    def __init__(self, max_journal_size: int = 1000) -> None:
        self.max_journal_size = max_journal_size
        self._journal: List[GatewaySyncEvent] = []
        self._counter: int = 0
        self._applied_action_ids: set[str] = set()

    def record_event(
        self,
        event_type: GatewayEventType,
        payload: Dict[str, Any],
        device_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> GatewaySyncEvent:
        """Appends a new sync event to the journal and triggers real-time broadcast."""
        self._counter += 1
        event_id = f"evt_{self._counter:06d}"

        event = GatewaySyncEvent(
            event_id=event_id,
            event_type=event_type,
            device_id=device_id,
            payload=payload,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc),
        )

        self._journal.append(event)
        if len(self._journal) > self.max_journal_size:
            self._journal = self._journal[-self.max_journal_size:]

        # Asynchronous broadcast to connected devices
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(connection_manager.broadcast(event))
        except Exception:
            pass

        return event

    def get_events_since(self, last_event_id: Optional[str] = None) -> List[GatewaySyncEvent]:
        """Returns events that occurred after the given event ID."""
        if not last_event_id:
            return list(self._journal)

        for i, event in enumerate(self._journal):
            if event.event_id == last_event_id:
                return self._journal[i + 1:]

        # If last_event_id is unknown/stale, return all available events in journal
        return list(self._journal)

    def reconcile_offline_batch(self, req: SyncBatchRequest) -> SyncBatchResponse:
        """
        Idempotently executes queued offline actions and retrieves new events
        for the reconnecting device.
        """
        processed_action_ids: List[str] = []

        for item in req.offline_actions:
            if item.action_id in self._applied_action_ids:
                # Already processed — idempotent skip
                processed_action_ids.append(item.action_id)
                continue

            success = self._apply_offline_action(item)
            if success:
                self._applied_action_ids.add(item.action_id)
                processed_action_ids.append(item.action_id)

        # Retrieve new events since client's last watermark
        new_events = self.get_events_since(req.last_event_id)
        latest_id = self._journal[-1].event_id if self._journal else None

        return SyncBatchResponse(
            events=new_events,
            processed_action_ids=processed_action_ids,
            latest_event_id=latest_id,
            server_time=datetime.now(timezone.utc),
        )

    def _apply_offline_action(self, item: OfflineActionItem) -> bool:
        """Applies a single offline action to downstream microservices."""
        logger.info(f"Applying offline action '{item.action_type}' (ID: {item.action_id})")
        try:
            if item.action_type == "resolve_approval":
                approval_id = item.payload.get("approval_id")
                approved = item.payload.get("approved", True)
                reason = item.payload.get("reason")
                with httpx.Client(base_url=settings.TASK_SERVICE_URL, timeout=5.0) as client:
                    res = client.post(
                        f"/api/v1/approvals/{approval_id}/resolve",
                        json={"approved": approved, "reason": reason},
                    )
                    return res.status_code == 200

            elif item.action_type == "dispatch_prompt":
                prompt = item.payload.get("prompt")
                device_context = item.payload.get("device_context", "android")
                with httpx.Client(base_url=settings.ROUTER_SERVICE_URL, timeout=10.0) as client:
                    res = client.post(
                        "/api/v1/router/dispatch",
                        json={"prompt": prompt, "device_context": device_context},
                    )
                    return res.status_code == 200

            elif item.action_type == "dismiss_reminder":
                reminder_id = item.payload.get("reminder_id")
                with httpx.Client(base_url=settings.AUTOMATION_SERVICE_URL, timeout=5.0) as client:
                    res = client.post(f"/api/v1/reminders/{reminder_id}/dismiss", json={})
                    return res.status_code == 200

            else:
                logger.warning(f"Unknown offline action type: '{item.action_type}'")
                return True
        except Exception as e:
            logger.error(f"Failed to apply offline action '{item.action_id}': {e}")
            return False


sync_engine = SyncEngine()

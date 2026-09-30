import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from contracts.reminders.models import (
    ReminderCreateRequest,
    ReminderResponse,
    ReminderStatus,
)
from automation_service.repository.in_memory import InMemoryReminderRepository, reminder_repo

logger = logging.getLogger("automation_service.scheduler")


class ReminderScheduler:
    def __init__(self, repo: InMemoryReminderRepository = reminder_repo) -> None:
        self.repo = repo

    def create_reminder(self, req: ReminderCreateRequest) -> ReminderResponse:
        now = datetime.now(timezone.utc)
        reminder_id = str(uuid.uuid4())

        # If trigger_at doesn't have timezone info, assume UTC
        trigger = req.trigger_at
        if trigger.tzinfo is None:
            trigger = trigger.replace(tzinfo=timezone.utc)

        reminder = ReminderResponse(
            id=reminder_id,
            title=req.title,
            description=req.description,
            trigger_at=trigger,
            cron_expression=req.cron_expression,
            status=ReminderStatus.PENDING,
            target_device=req.target_device,
            metadata=req.metadata,
            created_at=now,
            updated_at=now,
        )

        logger.info(f"Created reminder '{reminder.title}' (ID: {reminder.id}) triggering at {reminder.trigger_at}")
        return self.repo.save(reminder)

    def check_due_reminders(self, now: Optional[datetime] = None) -> List[ReminderResponse]:
        """Scans for due reminders and marks them as DUE."""
        current_time = now or datetime.now(timezone.utc)
        due_items = self.repo.get_due(current_time)

        newly_due = []
        for r in due_items:
            if r.status == ReminderStatus.PENDING:
                r.status = ReminderStatus.DUE
                r.updated_at = current_time
                self.repo.save(r)
                newly_due.append(r)
                logger.info(f"Reminder DUE: '{r.title}' (ID: {r.id}) for target device '{r.target_device}'")

        return due_items

    def dismiss_reminder(self, reminder_id: str) -> Optional[ReminderResponse]:
        reminder = self.repo.get(reminder_id)
        if not reminder:
            return None

        reminder.status = ReminderStatus.DISMISSED
        reminder.updated_at = datetime.now(timezone.utc)
        logger.info(f"Reminder dismissed: '{reminder.title}' (ID: {reminder.id})")
        return self.repo.save(reminder)

    def cancel_reminder(self, reminder_id: str) -> bool:
        reminder = self.repo.get(reminder_id)
        if not reminder:
            return False

        reminder.status = ReminderStatus.CANCELLED
        reminder.updated_at = datetime.now(timezone.utc)
        self.repo.save(reminder)
        logger.info(f"Reminder cancelled: '{reminder.title}' (ID: {reminder.id})")
        return True


reminder_scheduler = ReminderScheduler()

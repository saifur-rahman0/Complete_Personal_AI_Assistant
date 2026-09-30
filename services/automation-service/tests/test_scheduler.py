from datetime import datetime, timedelta, timezone
from contracts.reminders.models import ReminderCreateRequest, ReminderStatus
from automation_service.domain.scheduler import ReminderScheduler
from automation_service.repository.in_memory import InMemoryReminderRepository


def test_scheduler_lifecycle():
    repo = InMemoryReminderRepository()
    scheduler = ReminderScheduler(repo=repo)

    # 1. Schedule future reminder
    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    req = ReminderCreateRequest(
        title="Drink water",
        trigger_at=future,
    )
    r = scheduler.create_reminder(req)
    assert r.status == ReminderStatus.PENDING

    # 2. Check due when time hasn't passed
    due = scheduler.check_due_reminders(now=datetime.now(timezone.utc))
    assert len(due) == 0

    # 3. Fast-forward time past trigger
    due_later = scheduler.check_due_reminders(now=future + timedelta(seconds=1))
    assert len(due_later) == 1
    assert due_later[0].status == ReminderStatus.DUE

    # 4. Dismiss
    dismissed = scheduler.dismiss_reminder(r.id)
    assert dismissed.status == ReminderStatus.DISMISSED

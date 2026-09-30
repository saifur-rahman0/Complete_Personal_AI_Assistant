from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest
from contracts.reminders.models import ReminderStatus, ReminderTargetDevice
from automation_service.main import app
from automation_service.repository.in_memory import reminder_repo


@pytest.fixture(autouse=True)
def clean_repo():
    reminder_repo._reminders.clear()
    yield
    reminder_repo._reminders.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_create_and_list_reminders(client):
    trigger = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "title": "Check server backups",
        "description": "Verify external drive",
        "trigger_at": trigger.isoformat(),
        "target_device": "windows",
    }

    res = client.post("/api/v1/reminders", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Check server backups"
    assert data["status"] == ReminderStatus.PENDING
    assert data["target_device"] == ReminderTargetDevice.WINDOWS
    reminder_id = data["id"]

    # List all
    list_res = client.get("/api/v1/reminders")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["items"][0]["id"] == reminder_id


def test_due_reminders_and_dismiss(client):
    # Create reminder due in the past
    past_trigger = datetime.now(timezone.utc) - timedelta(minutes=5)
    payload = {
        "title": "Take vitamins",
        "trigger_at": past_trigger.isoformat(),
        "target_device": "android",
    }

    create_res = client.post("/api/v1/reminders", json=payload)
    assert create_res.status_code == 201
    reminder_id = create_res.json()["id"]

    # Check due reminders
    due_res = client.get("/api/v1/reminders/due")
    assert due_res.status_code == 200
    due_items = due_res.json()
    assert len(due_items) == 1
    assert due_items[0]["id"] == reminder_id
    assert due_items[0]["status"] == ReminderStatus.DUE

    # Dismiss reminder
    dismiss_res = client.post(f"/api/v1/reminders/{reminder_id}/dismiss")
    assert dismiss_res.status_code == 200
    assert dismiss_res.json()["status"] == ReminderStatus.DISMISSED


def test_cancel_reminder(client):
    trigger = datetime.now(timezone.utc) + timedelta(hours=2)
    create_res = client.post(
        "/api/v1/reminders",
        json={"title": "Team meeting", "trigger_at": trigger.isoformat()},
    )
    reminder_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/reminders/{reminder_id}")
    assert del_res.status_code == 204

    # Status is cancelled
    get_res = client.get(f"/api/v1/reminders/{reminder_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == ReminderStatus.CANCELLED

from datetime import datetime, timezone
from contracts.gateway.models import (
    GatewayEventType,
    OfflineActionItem,
    SyncBatchRequest,
)
from gateway.sync import SyncEngine


def test_sync_engine_record_and_get_events():
    engine = SyncEngine(max_journal_size=10)

    # 1. Record two events
    ev1 = engine.record_event(
        event_type=GatewayEventType.TASK_CREATED,
        payload={"task_id": "task-001", "title": "Test Task 1"},
        device_id="dev-windows-1",
        correlation_id="corr-1",
    )
    assert ev1.event_id == "evt_000001"
    assert ev1.event_type == GatewayEventType.TASK_CREATED

    ev2 = engine.record_event(
        event_type=GatewayEventType.TASK_UPDATED,
        payload={"task_id": "task-001", "status": "completed"},
        device_id="dev-windows-1",
        correlation_id="corr-2",
    )
    assert ev2.event_id == "evt_000002"

    # 2. Get all events
    all_events = engine.get_events_since()
    assert len(all_events) == 2
    assert all_events[0].event_id == "evt_000001"
    assert all_events[1].event_id == "evt_000002"

    # 3. Get events since ev1
    since_ev1 = engine.get_events_since(ev1.event_id)
    assert len(since_ev1) == 1
    assert since_ev1[0].event_id == "evt_000002"

    # 4. Get events since unknown ID should return all events
    fallback = engine.get_events_since("evt_unknown")
    assert len(fallback) == 2


def test_sync_engine_journal_capacity_limit():
    engine = SyncEngine(max_journal_size=3)

    for i in range(5):
        engine.record_event(
            event_type=GatewayEventType.TASK_CREATED,
            payload={"index": i},
        )

    # Only last 3 events kept
    events = engine.get_events_since()
    assert len(events) == 3
    assert events[0].payload["index"] == 2
    assert events[2].payload["index"] == 4


def test_sync_engine_reconcile_offline_batch_idempotency(monkeypatch):
    engine = SyncEngine()

    # Pre-populate journal with one event
    engine.record_event(
        event_type=GatewayEventType.REMINDER_TRIGGERED,
        payload={"reminder_id": "rem-01"},
    )

    action1 = OfflineActionItem(
        action_id="act-uuid-1",
        action_type="unknown_action_type",
        payload={"data": "test"},
        queued_at=datetime.now(timezone.utc),
    )

    req1 = SyncBatchRequest(
        device_id="phone-01",
        last_event_id=None,
        offline_actions=[action1],
    )

    res1 = engine.reconcile_offline_batch(req1)
    assert "act-uuid-1" in res1.processed_action_ids
    assert len(res1.events) == 1

    # Send the exact same action again — should be idempotently accepted and deduplicated
    req2 = SyncBatchRequest(
        device_id="phone-01",
        last_event_id="evt_000001",
        offline_actions=[action1],
    )
    res2 = engine.reconcile_offline_batch(req2)
    assert "act-uuid-1" in res2.processed_action_ids
    # Since last_event_id was evt_000001 and no new events were recorded, new events should be empty
    assert len(res2.events) == 0

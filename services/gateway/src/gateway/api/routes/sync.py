from typing import List, Optional
from fastapi import APIRouter, Query
from contracts.gateway.models import GatewaySyncEvent, SyncBatchRequest, SyncBatchResponse
from gateway.sync import sync_engine

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post("/batch", response_model=SyncBatchResponse, summary="Reconcile offline actions and sync events")
def reconcile_offline_batch(req: SyncBatchRequest) -> SyncBatchResponse:
    return sync_engine.reconcile_offline_batch(req)


@router.get("/events", response_model=List[GatewaySyncEvent], summary="Retrieve sync events after watermark")
def get_sync_events(last_event_id: Optional[str] = Query(default=None)) -> List[GatewaySyncEvent]:
    return sync_engine.get_events_since(last_event_id)

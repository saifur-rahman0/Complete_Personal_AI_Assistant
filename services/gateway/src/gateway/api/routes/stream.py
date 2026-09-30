import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from gateway.stream import connection_manager

logger = logging.getLogger("gateway.api.stream")
router = APIRouter(tags=["stream"])


@router.websocket("/ws/events/{device_id}")
async def websocket_event_stream(websocket: WebSocket, device_id: str):
    """Real-time bidirectional WebSocket event channel for mobile/desktop client."""
    await connection_manager.connect(device_id, websocket)
    try:
        while True:
            # Keep-alive heartbeat & client ping handling
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        connection_manager.disconnect(device_id, websocket)
    except Exception as e:
        logger.warning(f"WebSocket error on device '{device_id}': {e}")
        connection_manager.disconnect(device_id, websocket)


@router.get("/api/v1/stream/events", summary="Server-Sent Events (SSE) push stream for companion clients")
async def sse_event_stream():
    queue = connection_manager.subscribe_sse()

    async def event_generator():
        try:
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            connection_manager.unsubscribe_sse(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

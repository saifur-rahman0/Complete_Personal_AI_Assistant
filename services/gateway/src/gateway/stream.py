import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket
from contracts.gateway.models import GatewaySyncEvent

logger = logging.getLogger("gateway.stream")


class ConnectionManager:
    """Manages active WebSocket connections from Android and Windows clients."""

    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._sse_subscribers: List[asyncio.Queue] = []

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if device_id not in self._connections:
            self._connections[device_id] = set()
        self._connections[device_id].add(websocket)
        logger.info(f"Device '{device_id}' connected via WebSocket. (Total active: {len(self._connections[device_id])})")

    def disconnect(self, device_id: str, websocket: WebSocket) -> None:
        if device_id in self._connections:
            self._connections[device_id].discard(websocket)
            if not self._connections[device_id]:
                del self._connections[device_id]
        logger.info(f"Device '{device_id}' disconnected from WebSocket.")

    async def broadcast(self, event: GatewaySyncEvent) -> None:
        """Broadcasts an event to all connected devices and SSE listeners."""
        data_text = event.model_dump_json()

        # 1. Send to all WebSockets
        for device_id, sockets in list(self._connections.items()):
            for ws in list(sockets):
                try:
                    await ws.send_text(data_text)
                except Exception as e:
                    logger.warning(f"Error sending event to device '{device_id}': {e}")
                    sockets.discard(ws)

        # 2. Push to SSE queues
        for queue in list(self._sse_subscribers):
            try:
                queue.put_nowait(data_text)
            except Exception:
                pass

    async def send_to_device(self, device_id: str, event: GatewaySyncEvent) -> None:
        """Sends targeted event to a specific device's active sockets."""
        sockets = self._connections.get(device_id, set())
        data_text = event.model_dump_json()
        for ws in list(sockets):
            try:
                await ws.send_text(data_text)
            except Exception:
                sockets.discard(ws)

    def subscribe_sse(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._sse_subscribers.append(queue)
        return queue

    def unsubscribe_sse(self, queue: asyncio.Queue) -> None:
        if queue in self._sse_subscribers:
            self._sse_subscribers.remove(queue)


connection_manager = ConnectionManager()

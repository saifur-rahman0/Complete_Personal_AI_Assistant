from typing import Any, Dict, List
from fastapi import APIRouter, Request
from gateway.chat_store import chat_store

router = APIRouter(prefix="/api/v1/chats", tags=["chats"])


@router.get("", summary="Get synchronized cross-device chat messages")
def get_chat_history(limit: int = 50) -> List[Dict[str, Any]]:
    return chat_store.get_messages(limit=limit)


@router.post("", summary="Record a synchronized chat message")
async def record_chat_message(request: Request) -> Dict[str, Any]:
    body = await request.json()
    role = body.get("role", "user")
    text = body.get("text", "")
    device = body.get("device", "unknown")
    return chat_store.add_message(role=role, text=text, device=device)

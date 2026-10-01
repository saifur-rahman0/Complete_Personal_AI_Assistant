from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List
import uuid

logger = logging.getLogger("gateway.chat_store")


class ChatMessageStore:
    """Synchronized cross-device message store for PC and Companion apps."""

    def __init__(self, max_history: int = 200, persist_path: str | None = None) -> None:
        self.max_history = max_history
        self.persist_path = persist_path or os.environ.get(
            "CHAT_PERSIST_PATH",
            str(Path(__file__).resolve().parent.parent.parent / "chat_history.json"),
        )
        self._messages: List[Dict[str, Any]] = []
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        try:
            path = Path(self.persist_path)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._messages = json.load(f)
                    return
        except Exception as e:
            logger.debug(f"Could not load chat history from disk: {e}")

        # Default greeting if empty
        self._messages = [
            {
                "id": "msg_initial",
                "role": "assistant",
                "text": "Hello! I am your AI assistant. You can give me file management commands, search instructions, or ask questions.",
                "device": "system",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

    def _save_to_disk(self) -> None:
        try:
            path = Path(self.persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._messages[-self.max_history :], f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save chat history to disk: {e}")

    def add_message(
        self, role: str, text: str, device: str = "unknown"
    ) -> Dict[str, Any]:
        msg = {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": role,
            "text": text,
            "device": device,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(msg)
        if len(self._messages) > self.max_history:
            self._messages = self._messages[-self.max_history :]
        self._save_to_disk()
        return msg

    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._messages[-limit:]

    def update_task_message(self, task_id: str, new_text: str) -> bool:
        """Updates any placeholder 'Dispatched task... (Task ID: ...)' message with completed result."""
        updated = False
        target_str = f"Task ID: {task_id}"
        for msg in self._messages:
            if target_str in msg.get("text", ""):
                msg["text"] = new_text
                updated = True
        if updated:
            self._save_to_disk()
        return updated


chat_store = ChatMessageStore()

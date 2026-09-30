import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from contracts.memory.models import MemoryCategory, MemoryEntryResponse
from contracts.reminders.models import ReminderResponse, ReminderStatus


class InMemoryReminderRepository:
    def __init__(self) -> None:
        self._reminders: Dict[str, ReminderResponse] = {}

    def save(self, reminder: ReminderResponse) -> ReminderResponse:
        self._reminders[reminder.id] = reminder
        return reminder

    def get(self, reminder_id: str) -> Optional[ReminderResponse]:
        return self._reminders.get(reminder_id)

    def list(self, status: Optional[ReminderStatus] = None) -> List[ReminderResponse]:
        items = list(self._reminders.values())
        if status:
            items = [r for r in items if r.status == status]
        return sorted(items, key=lambda x: x.trigger_at)

    def get_due(self, now: Optional[datetime] = None) -> List[ReminderResponse]:
        current_time = now or datetime.now(timezone.utc)
        return [
            r
            for r in self._reminders.values()
            if r.status in (ReminderStatus.PENDING, ReminderStatus.DUE)
            and r.trigger_at <= current_time
        ]

    def delete(self, reminder_id: str) -> bool:
        if reminder_id in self._reminders:
            del self._reminders[reminder_id]
            return True
        return False


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self._entries: Dict[str, MemoryEntryResponse] = {}
        self._vectors: Dict[str, List[float]] = {}

    def save(
        self,
        entry: MemoryEntryResponse,
        vector: Optional[List[float]] = None,
    ) -> MemoryEntryResponse:
        self._entries[entry.id] = entry
        if vector:
            self._vectors[entry.id] = vector
        return entry

    def get(self, entry_id: str) -> Optional[MemoryEntryResponse]:
        return self._entries.get(entry_id)

    def list(self, category: Optional[MemoryCategory] = None) -> List[MemoryEntryResponse]:
        entries = list(self._entries.values())
        if category:
            entries = [e for e in entries if e.category == category]
        return sorted(entries, key=lambda x: x.created_at, reverse=True)

    def search(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        category: Optional[MemoryCategory] = None,
        limit: int = 5,
        min_similarity: float = 0.2,
    ) -> List[MemoryEntryResponse]:
        results: List[Tuple[float, MemoryEntryResponse]] = []
        query_tokens = set(query.lower().split())

        for entry_id, entry in self._entries.items():
            if category and entry.category != category:
                continue

            similarity = 0.0

            # 1. Cosine similarity if vectors exist
            if query_vector and entry_id in self._vectors:
                entry_vector = self._vectors[entry_id]
                similarity = self._cosine_similarity(query_vector, entry_vector)
            else:
                # 2. Token overlap similarity fallback
                entry_tokens = set(entry.content.lower().split())
                if query_tokens and entry_tokens:
                    overlap = query_tokens.intersection(entry_tokens)
                    similarity = len(overlap) / max(len(query_tokens), 1)

            if similarity >= min_similarity:
                entry_copy = entry.model_copy()
                entry_copy.similarity = round(similarity, 3)
                results.append((similarity, entry_copy))

        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


reminder_repo = InMemoryReminderRepository()
memory_repo = InMemoryMemoryRepository()

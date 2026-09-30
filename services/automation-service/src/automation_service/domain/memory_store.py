import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from contracts.memory.models import (
    MemoryCategory,
    MemoryEntryCreate,
    MemoryEntryResponse,
    MemorySearchRequest,
)
from automation_service.config import settings
from automation_service.repository.in_memory import InMemoryMemoryRepository, memory_repo

logger = logging.getLogger("automation_service.memory")


class ContextualMemoryStore:
    def __init__(self, repo: InMemoryMemoryRepository = memory_repo) -> None:
        self.repo = repo

    def store_memory(self, req: MemoryEntryCreate) -> MemoryEntryResponse:
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        entry = MemoryEntryResponse(
            id=entry_id,
            content=req.content,
            category=req.category,
            metadata=req.metadata,
            similarity=None,
            created_at=now,
        )

        vector = self._get_embedding(req.content)
        saved = self.repo.save(entry, vector=vector)
        logger.info(f"Stored memory (category='{saved.category}', ID: {saved.id}): '{saved.content[:40]}...'")
        return saved

    def search_memory(self, req: MemorySearchRequest) -> List[MemoryEntryResponse]:
        query_vector = self._get_embedding(req.query)
        results = self.repo.search(
            query=req.query,
            query_vector=query_vector,
            category=req.category,
            limit=req.limit,
            min_similarity=req.min_similarity,
        )
        return results

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Attempts to fetch vector embedding from local Ollama instance."""
        try:
            with httpx.Client(base_url=settings.OLLAMA_BASE_URL, timeout=2.0) as client:
                res = client.post(
                    "/api/embeddings",
                    json={"model": settings.EMBEDDING_MODEL, "prompt": text},
                )
                if res.status_code == 200:
                    data = res.json()
                    return data.get("embedding")
        except Exception:
            # Expected when Ollama is offline or model not pulled; graceful fallback
            pass
        return None


contextual_memory_store = ContextualMemoryStore()

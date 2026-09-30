from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from contracts.memory.models import (
    MemoryCategory,
    MemoryEntryCreate,
    MemoryEntryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
)
from automation_service.domain.memory_store import contextual_memory_store
from automation_service.repository.in_memory import memory_repo

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.post(
    "",
    response_model=MemoryEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a memory fact or note",
)
def store_memory(req: MemoryEntryCreate) -> MemoryEntryResponse:
    return contextual_memory_store.store_memory(req)


@router.post(
    "/search",
    response_model=MemorySearchResponse,
    summary="Semantic retrieval of relevant memories",
)
def search_memory(req: MemorySearchRequest) -> MemorySearchResponse:
    results = contextual_memory_store.search_memory(req)
    return MemorySearchResponse(results=results, total=len(results))


@router.get(
    "",
    response_model=List[MemoryEntryResponse],
    summary="List all memories",
)
def list_memories(
    category: Optional[MemoryCategory] = Query(default=None, description="Filter by category"),
) -> List[MemoryEntryResponse]:
    return memory_repo.list(category=category)


@router.get(
    "/{entry_id}",
    response_model=MemoryEntryResponse,
    summary="Get single memory entry",
)
def get_memory(entry_id: str) -> MemoryEntryResponse:
    entry = memory_repo.get(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory entry '{entry_id}' not found")
    return entry

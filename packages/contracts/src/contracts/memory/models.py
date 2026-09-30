from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryCategory(str, Enum):
    PREFERENCE = "preference"
    FACT = "fact"
    NOTE = "note"
    CONTEXT = "context"


class MemoryEntryCreate(BaseModel):
    content: str = Field(..., description="Fact or note content to remember", min_length=1)
    category: MemoryCategory = Field(default=MemoryCategory.NOTE, description="Category of memory")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata attributes")


class MemoryEntryResponse(BaseModel):
    id: str = Field(..., description="Unique memory entry ID")
    content: str
    category: MemoryCategory
    metadata: Dict[str, Any] = Field(default_factory=dict)
    similarity: Optional[float] = Field(default=None, description="Relevance score between 0.0 and 1.0 when queried")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemorySearchRequest(BaseModel):
    query: str = Field(..., description="Search query or context to match against memory", min_length=1)
    category: Optional[MemoryCategory] = Field(default=None, description="Optional category filter")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of items to return")
    min_similarity: float = Field(default=0.2, ge=0.0, le=1.0, description="Minimum relevance score threshold")


class MemorySearchResponse(BaseModel):
    results: List[MemoryEntryResponse]
    total: int

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl


class WebSourceResult(BaseModel):
    url: str = Field(..., description="Target webpage URL")
    title: str = Field(default="", description="Extracted page title")
    content_markdown: str = Field(default="", description="Sanitized markdown text content")
    snippet: str = Field(default="", description="Brief preview snippet")
    status: str = Field(default="success", description="Status: 'success', 'blocked_ssrf', 'error'")
    error_message: Optional[str] = None


class ResearchRequest(BaseModel):
    query: str = Field(..., description="Research query or topic", min_length=2)
    target_urls: Optional[List[str]] = Field(default=None, description="Explicit URLs to research, if known")
    max_sources: int = Field(default=3, ge=1, le=10, description="Max web pages to retrieve")
    extract_full_text: bool = Field(default=True, description="Whether to extract complete markdown body")


class ResearchReport(BaseModel):
    id: str = Field(..., description="Unique research report ID")
    query: str = Field(..., description="Original research query")
    summary: str = Field(..., description="Synthesized summary of findings")
    key_findings: List[str] = Field(default_factory=list, description="Bullet points of key takeaways")
    sources: List[WebSourceResult] = Field(default_factory=list, description="Referenced web sources")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

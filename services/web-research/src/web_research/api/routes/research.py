from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl
from contracts.research.models import ResearchReport, ResearchRequest, WebSourceResult
from web_research.crawler import safe_crawler
from web_research.synthesizer import research_synthesizer

router = APIRouter(prefix="/api/v1/research", tags=["research"])

_REPORTS_CACHE: Dict[str, ResearchReport] = {}


class ExtractUrlRequest(BaseModel):
    url: str


@router.post(
    "/extract",
    response_model=WebSourceResult,
    summary="Safely crawl and extract clean markdown from a single URL",
)
def extract_url(req: ExtractUrlRequest) -> WebSourceResult:
    return safe_crawler.fetch_page(req.url)


@router.post(
    "/search",
    response_model=ResearchReport,
    summary="Perform multi-source web research and generate synthesized report",
)
def perform_research(req: ResearchRequest) -> ResearchReport:
    sources = safe_crawler.search_and_crawl(
        query=req.query,
        target_urls=req.target_urls,
        max_sources=req.max_sources,
    )
    report = research_synthesizer.synthesize_report(query=req.query, sources=sources)
    _REPORTS_CACHE[report.id] = report
    return report


@router.get(
    "/reports/{report_id}",
    response_model=ResearchReport,
    summary="Retrieve previously generated research report",
)
def get_report(report_id: str) -> ResearchReport:
    report = _REPORTS_CACHE.get(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found")
    return report

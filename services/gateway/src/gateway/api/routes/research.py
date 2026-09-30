from fastapi import APIRouter, HTTPException, Request, status
import httpx
from gateway.config import settings

router = APIRouter(prefix="/api/v1/research", tags=["research"])


@router.post("/search", summary="Perform web research via web-research service")
async def perform_research(request: Request):
    body = await request.json()
    try:
        async with httpx.AsyncClient(base_url=settings.WEB_RESEARCH_SERVICE_URL, timeout=20.0) as client:
            resp = await client.post("/api/v1/research/search", json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/extract", summary="Extract clean markdown from URL via web-research service")
async def extract_url(request: Request):
    body = await request.json()
    try:
        async with httpx.AsyncClient(base_url=settings.WEB_RESEARCH_SERVICE_URL, timeout=10.0) as client:
            resp = await client.post("/api/v1/research/extract", json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

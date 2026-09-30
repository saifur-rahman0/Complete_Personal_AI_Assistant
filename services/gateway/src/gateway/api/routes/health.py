import asyncio
import time
from typing import Any, Dict, List
from fastapi import APIRouter, Query
import httpx
from gateway.audit import AuditLogEntry, audit_logger
from gateway.config import settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "port": settings.PORT,
    }


@router.get("/ready")
def readiness_check():
    return {
        "status": "ok",
        "downstream": {
            "task_service": settings.TASK_SERVICE_URL,
            "router_service": settings.ROUTER_SERVICE_URL,
            "automation_service": settings.AUTOMATION_SERVICE_URL,
            "web_research_service": settings.WEB_RESEARCH_SERVICE_URL,
        },
    }


async def _probe_service(name: str, url: str) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            is_ok = resp.status_code == 200
            return {
                "name": name,
                "status": "online" if is_ok else "unhealthy",
                "status_code": resp.status_code,
                "latency_ms": elapsed_ms,
                "url": url,
            }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "name": name,
            "status": "offline",
            "error": str(e),
            "latency_ms": elapsed_ms,
            "url": url,
        }


@router.get("/health/cluster", summary="Aggregated cluster health status across all microservices")
async def cluster_health():
    """
    Asynchronously queries all downstream microservices and returns
    comprehensive system topology status.
    """
    probes = [
        _probe_service("task-service", f"{settings.TASK_SERVICE_URL}/health"),
        _probe_service("decision-router", f"{settings.ROUTER_SERVICE_URL}/health"),
        _probe_service("automation-service", f"{settings.AUTOMATION_SERVICE_URL}/health"),
        _probe_service("web-research", f"{settings.WEB_RESEARCH_SERVICE_URL}/health"),
    ]

    results = await asyncio.gather(*probes)
    online_count = sum(1 for r in results if r["status"] == "online")
    total_count = len(results)

    cluster_status = "healthy" if online_count == total_count else ("degraded" if online_count > 0 else "offline")

    return {
        "cluster_status": cluster_status,
        "online_services": f"{online_count}/{total_count}",
        "gateway": {
            "name": settings.SERVICE_NAME,
            "port": settings.PORT,
            "status": "online",
        },
        "services": {r["name"]: r for r in results},
    }


@router.get("/api/v1/audit/logs", response_model=List[AuditLogEntry], summary="Retrieve recent security audit logs")
def get_audit_logs(limit: int = Query(default=50, ge=1, le=200)) -> List[AuditLogEntry]:
    return audit_logger.list_entries(limit=limit)

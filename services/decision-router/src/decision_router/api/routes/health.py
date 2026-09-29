from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str = "ok"
    service: str = "decision-router"


@router.get("/health", response_model=HealthStatus)
def health_check() -> HealthStatus:
    return HealthStatus()


@router.get("/ready", response_model=HealthStatus)
def readiness_check() -> HealthStatus:
    return HealthStatus()

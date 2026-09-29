from fastapi import APIRouter
from decision_router.api.routes.health import router as health_router
from decision_router.api.routes.route import router as route_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(route_router)

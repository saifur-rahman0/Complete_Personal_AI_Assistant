from fastapi import APIRouter
from gateway.api.routes.devices import router as devices_router
from gateway.api.routes.dispatch import router as dispatch_router
from gateway.api.routes.health import router as health_router
from gateway.api.routes.reminders import router as reminders_router
from gateway.api.routes.research import router as research_router
from gateway.api.routes.stream import router as stream_router
from gateway.api.routes.sync import router as sync_router
from gateway.api.routes.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(dispatch_router)
api_router.include_router(tasks_router)
api_router.include_router(reminders_router)
api_router.include_router(research_router)
api_router.include_router(devices_router)
api_router.include_router(sync_router)
api_router.include_router(stream_router)

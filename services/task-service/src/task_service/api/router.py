from fastapi import APIRouter
from task_service.api.routes.health import router as health_router
from task_service.api.routes.tasks import router as tasks_router
from task_service.api.routes.approvals import router as approvals_router
from task_service.api.routes.devices import router as devices_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(tasks_router)
api_router.include_router(approvals_router)
api_router.include_router(devices_router)


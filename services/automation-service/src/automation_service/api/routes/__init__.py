from automation_service.api.routes.memory import router as memory_router
from automation_service.api.routes.reminders import router as reminders_router

__all__ = [
    "reminders_router",
    "memory_router",
]

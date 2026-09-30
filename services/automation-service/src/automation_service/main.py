import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from automation_service.api.routes import memory_router, reminders_router
from automation_service.config import settings
from automation_service.domain.scheduler import reminder_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("automation_service")


async def reminder_monitor_loop():
    """Background task checking periodically for due reminders."""
    while True:
        try:
            due = reminder_scheduler.check_due_reminders()
            if due:
                logger.info(f"[MONITOR] Currently {len(due)} reminder(s) due!")
        except Exception as e:
            logger.error(f"Error checking due reminders: {e}", exc_info=True)
        await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.PORT}...")
    monitor_task = asyncio.create_task(reminder_monitor_loop())
    try:
        yield
    finally:
        logger.info(f"Shutting down {settings.SERVICE_NAME}...")
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="AI Workforce — Automation Service",
    description="Task scheduling, reminder triggers, and contextual memory service.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reminders_router)
app.include_router(memory_router)


@app.get("/health", tags=["system"])
def health_check():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "port": settings.PORT,
    }

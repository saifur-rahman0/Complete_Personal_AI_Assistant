import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from web_research.api.routes import research_router
from web_research.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("web_research")

app = FastAPI(
    title="AI Workforce — Web Research Service",
    description="SSRF-protected web research, crawling, and article extraction service.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)


@app.get("/health", tags=["system"])
def health_check():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "port": settings.PORT,
    }

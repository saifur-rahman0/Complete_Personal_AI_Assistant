import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from gateway.api.routes import api_router
from gateway.config import settings
from gateway.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gateway")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Workforce — API Gateway",
        description="Unified authenticated API Gateway, event streaming, and state synchronization.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=120, burst_limit=30)

    app.include_router(api_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway.main:app", host=settings.HOST, port=settings.PORT, reload=True)

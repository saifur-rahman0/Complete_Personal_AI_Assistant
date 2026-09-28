from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from task_service.api.router import api_router
from task_service.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions (e.g. database connection, broker connect)
    yield
    # Shutdown actions


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Workforce - Task Service",
        description="Core task lifecycle and authorization microservice",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Enable CORS for Flutter Android / Windows clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("task_service.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

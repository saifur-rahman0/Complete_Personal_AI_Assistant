from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from decision_router.api.router import api_router
from decision_router.classifiers.laya_classifier import neural_laya_classifier
from decision_router.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Asynchronously preload Neural Laya weights in background on startup
    if settings.USE_NEURAL_LAYA and neural_laya_classifier.is_available():
        neural_laya_classifier.load_model_background()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Workforce - Decision Router",
        description="System One fast intent classification and model dispatcher",
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

    app.include_router(api_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("decision_router.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

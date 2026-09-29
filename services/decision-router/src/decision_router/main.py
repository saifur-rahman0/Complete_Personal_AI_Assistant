from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from decision_router.api.router import api_router
from decision_router.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Workforce - Decision Router",
        description="System One fast intent classification and model dispatcher",
        version="0.1.0",
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

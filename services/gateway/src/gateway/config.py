import os
from pydantic import BaseModel


class GatewaySettings(BaseModel):
    SERVICE_NAME: str = "gateway"
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Downstream microservice endpoints
    TASK_SERVICE_URL: str = os.getenv("TASK_SERVICE_URL", "http://127.0.0.1:8001")
    ROUTER_SERVICE_URL: str = os.getenv("ROUTER_SERVICE_URL", "http://127.0.0.1:8002")
    AUTOMATION_SERVICE_URL: str = os.getenv("AUTOMATION_SERVICE_URL", "http://127.0.0.1:8003")
    WEB_RESEARCH_SERVICE_URL: str = os.getenv("WEB_RESEARCH_SERVICE_URL", "http://127.0.0.1:8004")

    # Security & Tokens
    AUTH_SECRET: str = os.getenv("GATEWAY_AUTH_SECRET", "dev-gateway-auth-secret-key-32b")
    TOKEN_TTL_HOURS: int = 24


settings = GatewaySettings()

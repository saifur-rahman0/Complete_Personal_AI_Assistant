from pydantic_settings import BaseSettings, SettingsConfigDict


class RouterSettings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    TASK_SERVICE_URL: str = "http://localhost:8001"
    AUTOMATION_SERVICE_URL: str = "http://localhost:8003"
    WEB_RESEARCH_SERVICE_URL: str = "http://localhost:8004"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    SLM_MODEL: str = "qwen2.5:1.5b"

    # Millisecond threshold for fast path vs slow path
    CONFIDENCE_THRESHOLD: float = 0.75

    # System One Neural Laya classifier configuration
    USE_NEURAL_LAYA: bool = False
    LAYA_MODEL_NAME: str = "convaiinnovations/laya"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = RouterSettings()

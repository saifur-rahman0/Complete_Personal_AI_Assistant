from pydantic_settings import BaseSettings, SettingsConfigDict


class RouterSettings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    TASK_SERVICE_URL: str = "http://localhost:8001"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    SLM_MODEL: str = "qwen2.5:1.5b"

    # Millisecond threshold for fast path vs slow path
    CONFIDENCE_THRESHOLD: float = 0.75

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = RouterSettings()

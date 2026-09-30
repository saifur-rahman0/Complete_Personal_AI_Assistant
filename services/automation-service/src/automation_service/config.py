from pydantic_settings import BaseSettings, SettingsConfigDict


class AutomationSettings(BaseSettings):
    SERVICE_NAME: str = "automation-service"
    PORT: int = 8003
    POLL_INTERVAL_SECONDS: float = 1.0
    TASK_SERVICE_URL: str = "http://localhost:8001"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = AutomationSettings()

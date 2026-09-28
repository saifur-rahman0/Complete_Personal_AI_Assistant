from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./task_service.db"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

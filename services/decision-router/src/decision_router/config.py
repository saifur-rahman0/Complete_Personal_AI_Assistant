from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"


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

    # Online Cloud LLM provider configuration
    ONLINE_LLM_PROVIDER: str = "auto"  # "auto", "gemini", "groq", "openai", "ollama"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    model_config = SettingsConfigDict(
        env_file=(".env", str(_ROOT_ENV)),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = RouterSettings()

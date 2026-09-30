from pydantic_settings import BaseSettings, SettingsConfigDict


class WebResearchSettings(BaseSettings):
    SERVICE_NAME: str = "web-research"
    PORT: int = 8004
    REQUEST_TIMEOUT_SECONDS: float = 8.0
    MAX_CONTENT_LENGTH_BYTES: int = 1_000_000
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = WebResearchSettings()

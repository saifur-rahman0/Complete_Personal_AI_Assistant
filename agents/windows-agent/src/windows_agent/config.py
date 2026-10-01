from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    TASK_SERVICE_URL: str = "http://localhost:8001"
    DEVICE_ID: str = "windows-laptop-01"
    POLL_INTERVAL_SECONDS: float = 0.5
    ALLOWED_ROOT_PATHS: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_allowed_roots(self) -> List[Path]:
        """Returns the list of canonical paths where filesystem operations are permitted."""
        if self.ALLOWED_ROOT_PATHS.strip():
            raw_paths = [p.strip() for p in self.ALLOWED_ROOT_PATHS.split(",") if p.strip()]
            return [Path(p).resolve() for p in raw_paths]

        # Default safe user locations
        user_home = Path.home()
        defaults = [
            user_home / "Downloads",
            user_home / "Documents",
            user_home / "Desktop",
            Path.cwd().resolve(),
        ]
        return [p.resolve() for p in defaults if p.exists()]


settings = AgentSettings()

import os
from typing import Any

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoRAG Architect"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database (SQLAlchemy connection string)
    DATABASE_URL: str = "sqlite:///./autorag.db"

    # Task queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS: comma-separated list of allowed origins.
    # Leave empty to allow all origins (local dev only).
    ALLOWED_ORIGINS: str = ""

    # File upload limits
    MAX_UPLOAD_MB: int = 50

    # Embedding defaults
    DEFAULT_EMBEDDING_MODEL: str = "huggingface_bge"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


class ConfigLoader:
    """Centralised configuration loader for YAML resource files."""

    def __init__(self, config_dir: str = "configs"):
        self.config_dir = os.path.join(os.getcwd(), config_dir)
        self._configs: dict[str, Any] = {}
        self.load_all()

    def load_all(self) -> None:
        """Load all YAML files present in the configuration directory."""
        if not os.path.exists(self.config_dir):
            import logging

            logging.getLogger(__name__).warning(
                "Configuration directory '%s' not found.", self.config_dir
            )
            return

        for filename in os.listdir(self.config_dir):
            if filename.endswith((".yaml", ".yml")):
                name = filename.split(".")[0]
                filepath = os.path.join(self.config_dir, filename)
                with open(filepath, encoding="utf-8") as f:
                    self._configs[name] = yaml.safe_load(f)

    def get(self, section: str, default: Any | None = None) -> Any:
        """Return a specific configuration section by name."""
        return self._configs.get(section, default)

    def get_nested(self, path: str, default: Any | None = None) -> Any:
        """Return a deeply nested configuration value using dot notation."""
        keys = path.split(".")
        current: Any = self._configs
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current


# Global configuration instance (YAML files)
config = ConfigLoader()

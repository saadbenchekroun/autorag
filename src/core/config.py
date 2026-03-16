import os
from typing import Any, Dict, Optional

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoRAG Architect"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Metadata DB
    DATABASE_URL: str = "sqlite:///./autorag.db"

    # Redis/Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        case_sensitive = True


settings = Settings()


class ConfigLoader:
    """Centralized configuration loader for YAML resource files."""

    def __init__(self, config_dir: str = "configs"):
        self.config_dir = os.path.join(os.getcwd(), config_dir)
        self._configs: Dict[str, Any] = {}
        self.load_all()

    def load_all(self) -> None:
        """Loads all YAML files present in the configuration directory."""
        if not os.path.exists(self.config_dir):
            print(f"Warning: Configuration directory '{self.config_dir}' not found.")
            return

        for filename in os.listdir(self.config_dir):
            if filename.endswith((".yaml", ".yml")):
                name = filename.split(".")[0]
                filepath = os.path.join(self.config_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    self._configs[name] = yaml.safe_load(f)

    def get(self, section: str, default: Optional[Any] = None) -> Any:
        """Get a specific configuration section by name."""
        return self._configs.get(section, default)

    def get_nested(self, path: str, default: Optional[Any] = None) -> Any:
        """Get a deeply nested configuration value using dot notation."""
        keys = path.split(".")
        current = self._configs
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current


# Global configuration instance for YAML files
config = ConfigLoader()

"""
Configuration management

Centralized settings using Pydantic BaseSettings for type-safe configuration
with environment variable support.

IMPORTANT: Uses dynamic path resolution from paths.py to work from any directory.
"""

import logging
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from .paths import (
    get_credentials_file,
    get_database_file,
    get_frontend_dist_dir,
    get_package_root,
    get_playwright_browsers_dir,
)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings with environment variable support

    Settings can be overridden via environment variables:
    - DATABASE_PATH=/custom/path/db.sqlite
    - API_PORT=8000
    - ENVIRONMENT=development
    """

    # Database (defaults to dynamic path from paths.py)
    database_path: Path = get_database_file()

    # Credentials (defaults to dynamic path from paths.py)
    vault_path: Path = get_credentials_file()

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 5000
    api_workers: int = 1
    cors_origins: list[str] = ["*"]
    websocket_api_key: str = ""  # Will be auto-generated if not set

    def __init__(self, **kwargs):
        """Initialize settings and generate secure API key if not provided"""
        super().__init__(**kwargs)

        # Generate secure random API key if not set or if using old default
        if not self.websocket_api_key or self.websocket_api_key == "dev-key-change-in-production":
            self.websocket_api_key = secrets.token_urlsafe(32)
            logger.warning(
                "WEBSOCKET_API_KEY not set in environment - generated random key. "
                "Set WEBSOCKET_API_KEY in .env for production to persist across restarts."
            )

    # Environment
    environment: str = "production"
    log_level: str = "INFO"
    log_format: str = "json"

    # Playwright browser automation (defaults to dynamic path from paths.py)
    playwright_headless: bool = True
    playwright_browser: str = "chromium"
    playwright_timeout: int = 30000
    playwright_browsers_path: Path = get_playwright_browsers_dir()

    # Feature flags
    enable_ai: bool = False
    enable_browser_recording: bool = True
    enable_screenshot_streaming: bool = True

    # Execution
    max_concurrent_executions: int = 10
    execution_timeout_seconds: int = 3600  # 1 hour

    # Frontend (defaults to dynamic path from paths.py)
    frontend_dir: Path = get_frontend_dist_dir()

    # Filesystem browser security
    filesystem_allowed_paths: str = ""  # Colon-separated list of allowed directories

    model_config = SettingsConfigDict(
        env_file=str(get_package_root() / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Singleton pattern for settings
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get application settings (singleton)

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def is_dev_mode() -> bool:
    """
    Check if running in development mode

    Returns:
        bool: True if environment is development
    """
    settings = get_settings()
    return settings.environment.lower() in ("development", "dev")

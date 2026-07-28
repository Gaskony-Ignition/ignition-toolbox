"""
Configuration management

Centralized settings using Pydantic BaseSettings for type-safe configuration
with environment variable support.

Also provides environment setup and data directory management (consolidated
from the former ignition_toolkit.config module).

IMPORTANT: Uses dynamic path resolution from paths.py to work from any directory.
"""

import logging
import os
import secrets
import sys
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


# ============================================================
# Environment setup and data directory management
# (consolidated from ignition_toolkit.config)
# ============================================================


def _is_frozen() -> bool:
    """Check if running as a frozen PyInstaller executable."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def setup_environment():
    """
    Set up environment variables for consistent paths

    This must be called before any other imports that depend on environment variables
    (e.g., Playwright, which uses HOME for browser cache).

    When running as a frozen executable, uses IGNITION_TOOLKIT_DATA to avoid
    writing to protected directories like Program Files.
    """
    # Set consistent Playwright browsers path
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        if _is_frozen():
            # Frozen mode: use environment variable from Electron
            env_data = os.environ.get("IGNITION_TOOLKIT_DATA")
            if env_data:
                browsers_path = Path(env_data) / ".playwright-browsers"
            else:
                # Fallback to user home directory
                browsers_path = Path.home() / ".ignition-toolkit" / ".playwright-browsers"
        else:
            # Development mode: use package-relative path
            package_root = Path(__file__).parent.parent.parent.resolve()
            browsers_path = package_root / "data" / ".playwright-browsers"

        browsers_path.mkdir(parents=True, exist_ok=True)
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
        logger.debug(f"Set PLAYWRIGHT_BROWSERS_PATH={browsers_path}")


# Call setup immediately on module import
setup_environment()


def get_toolkit_data_dir() -> Path:
    """
    Get the toolkit data directory (credentials, database, etc.)

    Priority order:
    1. IGNITION_TOOLKIT_DATA environment variable (if set, or if frozen)
    2. Project directory: <package_root>/data/.ignition-toolkit (development only)
    3. Fallback: ~/.ignition-toolkit (user's home directory)

    This ensures credentials are stored in a consistent location regardless
    of installation method or operating system, and avoids writing to
    protected directories like Program Files.

    Returns:
        Path to data directory
    """
    # Check environment variable override (always used in frozen mode)
    env_path = os.getenv("IGNITION_TOOLKIT_DATA")
    if env_path:
        path = Path(env_path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using data directory from IGNITION_TOOLKIT_DATA: {path}")
        return path

    # If running as frozen executable without env var, use home directory
    # This prevents attempting to write to Program Files
    if _is_frozen():
        fallback = Path.home() / ".ignition-toolkit"
        fallback.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using fallback data directory (frozen mode): {fallback}")
        return fallback

    # Calculate project root from package location
    package_root = Path(__file__).parent.parent.parent.resolve()

    # Check if we have a data/ directory at package root (development mode)
    project_data_dir = package_root / "data" / ".ignition-toolkit"
    if (package_root / "data").exists() or (package_root / "playbooks").exists():
        # We're in development mode - use project-relative directory
        project_data_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using project data directory: {project_data_dir}")
        return project_data_dir

    # Fallback to user's home directory (works on all platforms)
    fallback = Path.home() / ".ignition-toolkit"
    fallback.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Using fallback data directory: {fallback}")
    return fallback


def migrate_credentials_if_needed() -> None:
    """
    Check for credentials in old locations and migrate to new location

    Old locations (from when Path.home() was used):
    - /root/.config/claude-work/.ignition-toolkit/
    - /root/.config/claude-personal/.ignition-toolkit/
    - ~/.ignition-toolkit/ (wherever HOME pointed)

    If credentials are found in old location but not in new location,
    copy them over automatically.
    """
    new_location = get_toolkit_data_dir()

    # Don't migrate if new location already has credentials
    if (new_location / "credentials.json").exists():
        logger.debug(f"Credentials already exist in {new_location}, skipping migration")
        return

    # Check old locations (platform-independent)
    old_locations = [
        Path.home() / ".config" / "claude-work" / ".ignition-toolkit",
        Path.home() / ".config" / "claude-personal" / ".ignition-toolkit",
        Path.home() / ".ignition-toolkit",  # Standard location
    ]

    for old_location in old_locations:
        if old_location == new_location:
            continue  # Skip if it's the same as new location

        creds_file = old_location / "credentials.json"
        key_file = old_location / "encryption.key"
        db_file = old_location / "ignition_toolkit.db"

        if creds_file.exists() and key_file.exists():
            logger.info(f"Found credentials in old location: {old_location}")
            logger.info(f"Migrating to new location: {new_location}")

            # Create new location
            new_location.mkdir(parents=True, exist_ok=True)

            # Copy files
            import shutil

            shutil.copy2(creds_file, new_location / "credentials.json")
            shutil.copy2(key_file, new_location / "encryption.key")

            # Copy database if it exists and has data
            if db_file.exists() and db_file.stat().st_size > 0:
                dest_db = new_location / "ignition_toolkit.db"
                # Only copy if destination doesn't exist or is smaller
                if not dest_db.exists() or dest_db.stat().st_size < db_file.stat().st_size:
                    shutil.copy2(db_file, dest_db)
                    logger.info(f"  - Copied database: {db_file.stat().st_size} bytes")

            # Copy metadata if it exists
            metadata_file = old_location / "playbook_metadata.json"
            if metadata_file.exists():
                shutil.copy2(metadata_file, new_location / "playbook_metadata.json")

            logger.info(f"Migration complete from {old_location}")
            return  # Only migrate from first found location

    logger.debug("No old credentials found to migrate")


# ============================================================
# Pydantic Settings
# ============================================================


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
    api_host: str = "127.0.0.1"
    api_port: int = 5000
    api_workers: int = 1
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5000",
        "app://.",
        "file://",
    ]
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

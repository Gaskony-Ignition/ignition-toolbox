"""
Configuration and paths for Ignition Toolkit

Provides consistent, environment-independent paths for data storage.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_environment():
    """
    Set up environment variables for consistent paths

    This must be called before any other imports that depend on environment variables
    (e.g., Playwright, which uses HOME for browser cache).
    """
    # Set consistent Playwright browsers path
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        # Calculate from package location instead of hardcoded path
        package_root = Path(__file__).parent.parent.resolve()
        browsers_path = package_root / "data" / ".playwright-browsers"
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
        logger.debug(f"Set PLAYWRIGHT_BROWSERS_PATH={browsers_path}")


# Call setup immediately on module import
setup_environment()


def get_toolkit_data_dir() -> Path:
    """
    Get the toolkit data directory (credentials, database, etc.)

    Priority order:
    1. IGNITION_TOOLKIT_DATA environment variable (if set)
    2. Project directory: <package_root>/data/.ignition-toolkit
    3. Fallback: ~/.ignition-toolkit (user's home directory)

    This ensures credentials are stored in a consistent location regardless
    of installation method or operating system.

    Returns:
        Path to data directory
    """
    # Check environment variable override
    env_path = os.getenv("IGNITION_TOOLKIT_DATA")
    if env_path:
        path = Path(env_path).expanduser().resolve()
        logger.info(f"Using data directory from IGNITION_TOOLKIT_DATA: {path}")
        return path

    # Calculate project root from package location
    package_root = Path(__file__).parent.parent.resolve()

    # Check if we have a data/ directory at package root (development mode)
    project_data_dir = package_root / "data" / ".ignition-toolkit"
    if (package_root / "data").exists() or (package_root / "playbooks").exists():
        # We're in development mode - use project-relative directory
        logger.debug(f"Using project data directory: {project_data_dir}")
        return project_data_dir

    # Fallback to user's home directory (works on all platforms)
    fallback = Path.home() / ".ignition-toolkit"
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

            logger.info(f"✓ Migration complete from {old_location}")
            return  # Only migrate from first found location

    logger.debug("No old credentials found to migrate")

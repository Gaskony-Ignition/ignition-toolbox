"""
Configuration and path information API

Provides runtime configuration and dynamic path information
to enable frontend portability.
"""

import logging
import os
from fastapi import APIRouter

from ignition_toolkit.core.config import get_settings
from ignition_toolkit.core.paths import (
    get_playbooks_dir,
    get_package_root,
    get_user_data_dir,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
async def get_config():
    """
    Get runtime configuration and paths

    Returns dynamic configuration to enable frontend portability.
    Frontend can use these paths instead of hardcoding them.

    Returns:
        dict: Configuration including version, paths, and feature flags
    """
    # Version comes from the package itself; env var allows override for dev/CI
    from ignition_toolkit import __version__
    version = os.getenv("APP_VERSION", __version__)

    # Check if AI is enabled
    ai_enabled = bool(os.getenv("ANTHROPIC_API_KEY"))

    settings = get_settings()

    return {
        "version": version,
        "paths": {
            "playbooks_dir": str(get_playbooks_dir()),
            "package_root": str(get_package_root()),
            "user_data_dir": str(get_user_data_dir()),
        },
        "features": {
            "ai_enabled": ai_enabled,
            "browser_automation": True,
            "designer_automation": False,  # Future feature
        },
        "server": {
            "port": int(os.getenv("API_PORT", "5000")),
            "host": os.getenv("API_HOST", "0.0.0.0"),
        },
        # WebSocket API key: frontend fetches this once at startup via /api/config
        # Electron apps also receive it via IPC (electron/ipc/handlers.ts)
        "websocket_api_key": settings.websocket_api_key,
    }

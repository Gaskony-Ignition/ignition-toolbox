"""
Configuration and paths for Ignition Toolkit

DEPRECATED: This module is a backward-compatible re-export shim.
All configuration is now consolidated in ignition_toolkit.core.config.

Import from ignition_toolkit.core.config directly for new code.
"""

# Re-export everything from the consolidated config module
from ignition_toolkit.core.config import (
    Settings,
    get_settings,
    get_toolkit_data_dir,
    is_dev_mode,
    migrate_credentials_if_needed,
    setup_environment,
)

__all__ = [
    "get_toolkit_data_dir",
    "migrate_credentials_if_needed",
    "setup_environment",
    "get_settings",
    "is_dev_mode",
    "Settings",
]

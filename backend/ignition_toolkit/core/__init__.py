"""
Core module - Base abstractions and interfaces

Provides foundational components used across the toolkit:
- Interfaces and protocols
- Base exception hierarchy
- Configuration management
- Shared models
"""

from ignition_toolkit.core.config import (
    Settings,
    get_settings,
    get_toolkit_data_dir,
    is_dev_mode,
    migrate_credentials_if_needed,
    setup_environment,
)

__all__ = [
    "Settings",
    "get_settings",
    "get_toolkit_data_dir",
    "migrate_credentials_if_needed",
    "setup_environment",
    "is_dev_mode",
]

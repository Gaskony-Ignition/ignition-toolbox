"""
Core module - Base abstractions and interfaces

Provides foundational components used across the toolkit:
- Interfaces and protocols
- Base exception hierarchy
- Configuration management
- Shared models
"""

from ignition_toolkit.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]

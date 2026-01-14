"""
Gateway data models
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ModuleState(str, Enum):
    """Module installation state"""

    RUNNING = "running"
    LOADED = "loaded"
    INSTALLED = "installed"
    FAILED = "failed"


class ProjectStatus(str, Enum):
    """Project enabled/disabled status"""

    ENABLED = "enabled"
    DISABLED = "disabled"


class TagQuality(str, Enum):
    """Tag quality codes"""

    GOOD = "Good"
    BAD = "Bad"
    ERROR = "Error"
    UNCERTAIN = "Uncertain"


@dataclass
class Module:
    """
    Represents an Ignition module

    Attributes:
        name: Module name (e.g., "Perspective")
        version: Module version (e.g., "3.3.0")
        state: Current state (running, loaded, installed, failed)
        description: Module description
        license_required: Whether module requires a license
    """

    name: str
    version: str
    state: ModuleState
    description: str | None = None
    license_required: bool = False

    def __repr__(self) -> str:
        return f"Module(name='{self.name}', version='{self.version}', state='{self.state.value}')"


@dataclass
class Project:
    """
    Represents an Ignition project

    Attributes:
        name: Project name (unique identifier)
        title: Display title
        description: Project description
        enabled: Whether project is enabled
        parent: Parent project name (for inheritance)
        version: Project version
    """

    name: str
    title: str
    enabled: bool
    description: str | None = None
    parent: str | None = None
    version: str | None = None

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"Project(name='{self.name}', title='{self.title}', {status})"


@dataclass
class Tag:
    """
    Represents an Ignition tag

    Attributes:
        name: Tag name
        path: Full tag path (e.g., "/Sensors/Temperature")
        value: Current tag value
        quality: Tag quality code
        timestamp: Last update timestamp
        data_type: Tag data type (Int4, Float8, String, Boolean, etc.)
    """

    name: str
    path: str
    value: Any
    quality: TagQuality
    timestamp: datetime | None = None
    data_type: str | None = None

    def __repr__(self) -> str:
        return f"Tag(path='{self.path}', value={self.value}, quality='{self.quality.value}')"


@dataclass
class GatewayInfo:
    """
    Gateway system information

    Attributes:
        version: Ignition version (e.g., "8.3.4")
        platform_version: Build number
        edition: Edition (standard, edge, etc.)
        license_key: License key (partially masked)
        uptime_seconds: Gateway uptime in seconds
    """

    version: str
    platform_version: str
    edition: str
    license_key: str | None = None
    uptime_seconds: int | None = None

    def __repr__(self) -> str:
        return f"GatewayInfo(version='{self.version}', edition='{self.edition}')"


@dataclass
class HealthStatus:
    """
    Gateway health status

    Attributes:
        healthy: Overall health status
        uptime_seconds: Seconds since last restart
        thread_count: Number of active threads
        memory_used_mb: Memory usage in MB
        memory_max_mb: Maximum memory allocation in MB
    """

    healthy: bool
    uptime_seconds: int
    thread_count: int | None = None
    memory_used_mb: float | None = None
    memory_max_mb: float | None = None

    @property
    def memory_usage_percent(self) -> float | None:
        """Calculate memory usage percentage"""
        if self.memory_used_mb is not None and self.memory_max_mb is not None:
            return (self.memory_used_mb / self.memory_max_mb) * 100
        return None

    def __repr__(self) -> str:
        status = "healthy" if self.healthy else "unhealthy"
        return f"HealthStatus({status}, uptime={self.uptime_seconds}s)"

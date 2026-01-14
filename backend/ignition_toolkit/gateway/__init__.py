"""
Ignition Gateway REST API client

Provides async client for interacting with Ignition Gateway operations:
- Authentication
- Module management
- Project management
- Tag operations
- System operations (restart, backup, health checks)
"""

from ignition_toolkit.gateway.client import GatewayClient
from ignition_toolkit.gateway.exceptions import (
    AuthenticationError,
    GatewayConnectionError,
    GatewayException,
    ResourceNotFoundError,
)
from ignition_toolkit.gateway.models import (
    GatewayInfo,
    HealthStatus,
    Module,
    Project,
    Tag,
)

__all__ = [
    "GatewayClient",
    "Module",
    "Project",
    "Tag",
    "GatewayInfo",
    "HealthStatus",
    "GatewayException",
    "AuthenticationError",
    "ResourceNotFoundError",
    "GatewayConnectionError",
]

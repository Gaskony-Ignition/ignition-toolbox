"""
Startup module - Application initialization and lifecycle management

Provides robust startup validation, health checks, and lifecycle management
for the Ignition Automation Toolkit.
"""

from ignition_toolkit.startup.health import (
    ComponentHealth,
    HealthStatus,
    SystemHealth,
    get_health_state,
    set_component_degraded,
    set_component_healthy,
    set_component_unhealthy,
)
from ignition_toolkit.startup.lifecycle import is_dev_mode, lifespan

__all__ = [
    "HealthStatus",
    "ComponentHealth",
    "SystemHealth",
    "get_health_state",
    "set_component_healthy",
    "set_component_unhealthy",
    "set_component_degraded",
    "lifespan",
    "is_dev_mode",
]

"""
Health state management

Tracks component health and overall system readiness for monitoring
and debugging.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    """Health status for system components"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """
    Health information for a single component

    Attributes:
        status: Health status (healthy/degraded/unhealthy/unknown)
        message: Human-readable status message
        last_checked: When health was last checked
        error: Error message if unhealthy
    """

    status: HealthStatus
    message: str = ""
    last_checked: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return {
            "status": self.status.value,
            "message": self.message,
            "last_checked": self.last_checked.isoformat(),
            "error": self.error,
        }


@dataclass
class SystemHealth:
    """
    Global system health state

    Tracks overall system health and individual component health.
    Used for startup validation and health check endpoints.
    """

    overall: HealthStatus = HealthStatus.UNKNOWN
    ready: bool = False
    startup_time: datetime | None = None

    # Component health
    database: ComponentHealth = field(default_factory=lambda: ComponentHealth(HealthStatus.UNKNOWN))
    vault: ComponentHealth = field(default_factory=lambda: ComponentHealth(HealthStatus.UNKNOWN))
    playbooks: ComponentHealth = field(
        default_factory=lambda: ComponentHealth(HealthStatus.UNKNOWN)
    )
    frontend: ComponentHealth = field(default_factory=lambda: ComponentHealth(HealthStatus.UNKNOWN))
    scheduler: ComponentHealth = field(default_factory=lambda: ComponentHealth(HealthStatus.UNKNOWN))

    # Startup issues
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for API responses"""
        return {
            "overall": self.overall.value,
            "ready": self.ready,
            "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            "components": {
                "database": self.database.to_dict(),
                "vault": self.vault.to_dict(),
                "playbooks": self.playbooks.to_dict(),
                "frontend": self.frontend.to_dict(),
                "scheduler": self.scheduler.to_dict(),
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }


# Global health state (singleton)
_health_state = SystemHealth()


def get_health_state() -> SystemHealth:
    """
    Get current system health state

    Returns:
        SystemHealth instance
    """
    return _health_state


def set_component_healthy(component: str, message: str = "") -> None:
    """
    Mark a component as healthy

    Args:
        component: Component name (database, vault, playbooks, frontend)
        message: Optional status message
    """
    comp_health = ComponentHealth(HealthStatus.HEALTHY, message)
    setattr(_health_state, component, comp_health)


def set_component_unhealthy(component: str, error: str) -> None:
    """
    Mark a component as unhealthy

    Args:
        component: Component name
        error: Error message
    """
    comp_health = ComponentHealth(HealthStatus.UNHEALTHY, error=error)
    setattr(_health_state, component, comp_health)
    _health_state.errors.append(f"{component}: {error}")


def set_component_degraded(component: str, warning: str) -> None:
    """
    Mark a component as degraded

    Args:
        component: Component name
        warning: Warning message
    """
    comp_health = ComponentHealth(HealthStatus.DEGRADED, error=warning)
    setattr(_health_state, component, comp_health)
    _health_state.warnings.append(f"{component}: {warning}")


def reset_health_state() -> None:
    """Reset health state to initial values (for testing)"""
    global _health_state
    _health_state = SystemHealth()

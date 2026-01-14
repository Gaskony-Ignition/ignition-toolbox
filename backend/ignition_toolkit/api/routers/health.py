"""
Health check endpoints

Provides Kubernetes-style health check endpoints for monitoring and debugging:
- GET /health - Overall health check (healthy/degraded/unhealthy)
- GET /health/live - Liveness probe (always 200 if running)
- GET /health/ready - Readiness probe (200 if ready, 503 if not)
- GET /health/detailed - Detailed component-level health information
"""

from typing import Any

from fastapi import APIRouter, Response

from ignition_toolkit import __version__
from ignition_toolkit.startup.health import HealthStatus, get_health_state

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(response: Response) -> dict[str, Any]:
    """
    Overall health check

    Returns:
        200: System is healthy or degraded (can serve requests)
        503: System is unhealthy (cannot serve requests)

    Response includes:
        - status: "healthy", "degraded", or "unhealthy"
        - ready: Boolean indicating if system is ready
        - errors: List of error messages (if unhealthy)
        - warnings: List of warning messages (if degraded)
    """
    health = get_health_state()

    # Return 503 if unhealthy, 200 otherwise
    if health.overall == HealthStatus.UNHEALTHY:
        response.status_code = 503

    return {
        "status": health.overall.value,
        "ready": health.ready,
        "version": __version__,
        "errors": health.errors if health.errors else None,
        "warnings": health.warnings if health.warnings else None,
    }


@router.get("/live")
async def liveness_probe() -> dict[str, str]:
    """
    Liveness probe (Kubernetes-style)

    Always returns 200 if the application is running.
    Used to detect if the application needs to be restarted.

    Returns:
        200: Application is running
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness_probe(response: Response) -> dict[str, Any]:
    """
    Readiness probe (Kubernetes-style)

    Returns 200 if system is ready to serve requests, 503 otherwise.
    Used to determine if traffic should be routed to this instance.

    Returns:
        200: System is ready to serve requests
        503: System is not ready (still starting up or degraded)
    """
    health = get_health_state()

    # Return 503 if not ready or unhealthy
    if not health.ready or health.overall == HealthStatus.UNHEALTHY:
        response.status_code = 503

    return {
        "ready": health.ready,
        "status": health.overall.value,
    }


@router.get("/detailed")
async def detailed_health(response: Response) -> dict[str, Any]:
    """
    Detailed health check with component-level information

    Returns comprehensive health information including:
    - Overall system health
    - Individual component health (database, vault, playbooks, frontend)
    - Startup time
    - Errors and warnings

    Returns:
        200: System is healthy or degraded
        503: System is unhealthy
    """
    health = get_health_state()

    # Return 503 if unhealthy
    if health.overall == HealthStatus.UNHEALTHY:
        response.status_code = 503

    return health.to_dict()

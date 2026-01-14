"""
FastAPI dependency injection functions

Provides centralized access to application services through FastAPI's dependency injection.
"""

from fastapi import Request

from ignition_toolkit.api.services import AppServices


def get_services(request: Request) -> AppServices:
    """
    Get AppServices from request state

    Args:
        request: FastAPI request object

    Returns:
        AppServices instance

    Raises:
        RuntimeError: If services not initialized
    """
    if not hasattr(request.app.state, "services"):
        raise RuntimeError("Application services not initialized")

    return request.app.state.services

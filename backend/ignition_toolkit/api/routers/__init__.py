"""
API routers

Modular FastAPI routers for different API domains.
"""

from ignition_toolkit.api.routers.health import router as health_router

__all__ = ["health_router"]

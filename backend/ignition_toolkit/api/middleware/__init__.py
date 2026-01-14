"""
API Middleware Package

FastAPI middleware components for security and request handling.

PORTABILITY v4: Lightweight middleware with no external dependencies.
"""

from ignition_toolkit.api.middleware.rate_limit import RateLimitMiddleware
from ignition_toolkit.api.middleware.auth import (
    verify_api_key,
    localhost_only,
    is_auth_required,
    print_api_key_info,
    API_KEY,
)

__all__ = [
    "RateLimitMiddleware",
    "verify_api_key",
    "localhost_only",
    "is_auth_required",
    "print_api_key_info",
    "API_KEY",
]

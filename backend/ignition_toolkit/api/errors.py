"""
Standardized error handling for API

Provides consistent error responses and error handling decorators.
"""

import logging
from enum import Enum
from functools import wraps
from typing import Any, Callable

from fastapi import HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standard error codes for API responses"""

    PLAYBOOK_NOT_FOUND = "playbook_not_found"
    INVALID_PATH = "invalid_path"
    EXECUTION_NOT_FOUND = "execution_not_found"
    CREDENTIAL_NOT_FOUND = "credential_not_found"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"
    PERMISSION_DENIED = "permission_denied"
    RESOURCE_CONFLICT = "resource_conflict"
    TIMEOUT_ERROR = "timeout_error"


class ErrorResponse(BaseModel):
    """Standard error response format"""

    error: ErrorCode
    message: str
    details: dict[str, Any] | None = None


def create_error_response(
    code: ErrorCode,
    message: str,
    status_code: int = 400,
    details: dict | None = None,
) -> HTTPException:
    """
    Create standardized HTTPException

    Args:
        code: Error code enum value
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional error details

    Returns:
        HTTPException with standardized error response

    Example:
        raise create_error_response(
            ErrorCode.PLAYBOOK_NOT_FOUND,
            "Playbook 'test.yaml' not found",
            404,
            {"path": "test.yaml"}
        )
    """
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            error=code,
            message=message,
            details=details,
        ).dict(),
    )


def api_exception_handler(operation: str):
    """
    Decorator for consistent error handling in API routes

    Automatically logs exceptions and converts them to standardized error responses.
    Re-raises HTTPExceptions as-is.

    Args:
        operation: Description of the operation for logging

    Example:
        @router.post("")
        @api_exception_handler("start_execution")
        async def start_execution(request: ExecutionRequest):
            # ... operation logic ...
            return result
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Let FastAPI handle existing HTTPExceptions
                raise
            except FileNotFoundError as e:
                logger.warning(f"{operation} - File not found: {e}")
                raise create_error_response(
                    ErrorCode.PLAYBOOK_NOT_FOUND,
                    f"File not found: {str(e)}",
                    404,
                )
            except PermissionError as e:
                logger.error(f"{operation} - Permission denied: {e}")
                raise create_error_response(
                    ErrorCode.PERMISSION_DENIED,
                    f"Permission denied: {str(e)}",
                    403,
                )
            except TimeoutError as e:
                logger.error(f"{operation} - Timeout: {e}")
                raise create_error_response(
                    ErrorCode.TIMEOUT_ERROR,
                    f"Operation timed out: {str(e)}",
                    504,
                )
            except Exception as e:
                logger.exception(f"{operation} failed: {e}")
                raise create_error_response(
                    ErrorCode.INTERNAL_ERROR,
                    f"{operation} failed: {str(e)}",
                    500,
                )

        return wrapper

    return decorator

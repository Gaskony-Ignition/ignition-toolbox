"""
Standardized error handling for API

Provides consistent error responses and error handling decorators.
"""

import logging
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any

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
    recovery_hint: str | None = None
    details: dict[str, Any] | None = None


def create_error_response(
    code: ErrorCode,
    message: str,
    status_code: int = 400,
    details: dict | None = None,
    recovery_hint: str | None = None,
) -> HTTPException:
    """
    Create standardized HTTPException

    Args:
        code: Error code enum value
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional error details
        recovery_hint: Optional hint for how to resolve the error

    Returns:
        HTTPException with standardized error response

    Example:
        raise create_error_response(
            ErrorCode.PLAYBOOK_NOT_FOUND,
            "Playbook 'test.yaml' not found",
            404,
            {"path": "test.yaml"},
            "Check the playbook exists in the playbooks directory"
        )
    """
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            error=code,
            message=message,
            recovery_hint=recovery_hint,
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
                    recovery_hint="Check the file path is correct and the file exists. Verify file permissions.",
                )
            except PermissionError as e:
                logger.error(f"{operation} - Permission denied: {e}")
                raise create_error_response(
                    ErrorCode.PERMISSION_DENIED,
                    f"Permission denied: {str(e)}",
                    403,
                    recovery_hint="Check file permissions and ensure the application has write access. On Windows, check if file is locked by another process.",
                )
            except TimeoutError as e:
                logger.error(f"{operation} - Timeout: {e}")
                raise create_error_response(
                    ErrorCode.TIMEOUT_ERROR,
                    f"Operation timed out: {str(e)}",
                    504,
                    recovery_hint="The operation took too long. Try increasing timeout settings or check if the target system is responsive.",
                )
            except Exception as e:
                # Extract recovery hint from exception if available
                recovery_hint = getattr(e, "recovery_hint", None)
                logger.exception(f"{operation} failed: {e}")
                raise create_error_response(
                    ErrorCode.INTERNAL_ERROR,
                    f"{operation} failed: {str(e)}",
                    500,
                    recovery_hint=recovery_hint or "Check the application logs for more details. If the problem persists, restart the application.",
                )

        return wrapper

    return decorator

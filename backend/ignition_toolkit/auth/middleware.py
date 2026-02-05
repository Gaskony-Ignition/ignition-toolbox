"""
Authentication Middleware

FastAPI middleware and dependencies for API key authentication.
"""

import logging
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from ignition_toolkit.auth.api_keys import APIKey, get_api_key_manager
from ignition_toolkit.auth.rbac import Permission, get_rbac_manager
from ignition_toolkit.auth.audit import AuditEventType, get_audit_logger

logger = logging.getLogger(__name__)

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass
class CurrentUser:
    """Represents the current authenticated user"""
    api_key: APIKey | None = None
    is_authenticated: bool = False
    role: str = "anonymous"
    scopes: list[str] = field(default_factory=list)
    ip_address: str | None = None

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a permission"""
        rbac = get_rbac_manager()
        return rbac.check_permission(self.role, permission, self.scopes)


async def get_current_user(
    request: Request,
    api_key: str | None = Depends(api_key_header),
) -> CurrentUser:
    """
    FastAPI dependency to get current authenticated user

    Usage:
        @app.get("/protected")
        async def protected_route(user: CurrentUser = Depends(get_current_user)):
            if not user.is_authenticated:
                raise HTTPException(status_code=401)
    """
    # Get client IP
    ip_address = request.client.host if request.client else None

    # No API key provided - anonymous user
    if not api_key:
        return CurrentUser(
            is_authenticated=False,
            role="anonymous",
            ip_address=ip_address,
        )

    # Validate API key
    manager = get_api_key_manager()
    validated_key = manager.validate_key(api_key)

    if not validated_key:
        # Log failed authentication
        audit = get_audit_logger()
        audit.log(
            event_type=AuditEventType.AUTH_FAILED,
            ip_address=ip_address,
            details={"reason": "Invalid API key"},
            success=False,
        )
        return CurrentUser(
            is_authenticated=False,
            role="anonymous",
            ip_address=ip_address,
        )

    return CurrentUser(
        api_key=validated_key,
        is_authenticated=True,
        role=validated_key.role,
        scopes=validated_key.scopes,
        ip_address=ip_address,
    )


def require_auth(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """
    Dependency that requires authentication

    Usage:
        @app.get("/protected")
        async def protected_route(user: CurrentUser = Depends(require_auth)):
            # User is guaranteed to be authenticated
            pass
    """
    if not user.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return user


def require_permission(permission: Permission):
    """
    Dependency factory that requires a specific permission

    Usage:
        @app.post("/playbooks")
        async def create_playbook(
            user: CurrentUser = Depends(require_permission(Permission.PLAYBOOK_WRITE))
        ):
            pass
    """
    def dependency(user: CurrentUser = Depends(require_auth)) -> CurrentUser:
        if not user.has_permission(permission):
            # Log access denied
            audit = get_audit_logger()
            audit.log(
                event_type=AuditEventType.ACCESS_DENIED,
                user_id=user.api_key.user_id if user.api_key else None,
                api_key_id=user.api_key.id if user.api_key else None,
                ip_address=user.ip_address,
                details={"required_permission": permission.value, "user_role": user.role},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        return user

    return dependency


def require_role(role: str):
    """
    Dependency factory that requires a specific role

    Usage:
        @app.delete("/system/reset")
        async def reset_system(user: CurrentUser = Depends(require_role("admin"))):
            pass
    """
    def dependency(user: CurrentUser = Depends(require_auth)) -> CurrentUser:
        if user.role != role and user.role != "admin":
            audit = get_audit_logger()
            audit.log(
                event_type=AuditEventType.ACCESS_DENIED,
                user_id=user.api_key.user_id if user.api_key else None,
                api_key_id=user.api_key.id if user.api_key else None,
                ip_address=user.ip_address,
                details={"required_role": role, "user_role": user.role},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}",
            )
        return user

    return dependency


class AuthMiddleware:
    """
    Optional authentication middleware for request logging

    Note: FastAPI dependencies are preferred for auth checks.
    This middleware is for logging/monitoring purposes.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract API key from headers
        headers = dict(scope.get("headers", []))
        api_key = headers.get(b"x-api-key", b"").decode()

        # Log request (without sensitive data)
        path = scope.get("path", "")
        method = scope.get("method", "")
        client = scope.get("client", ("unknown", 0))

        logger.debug(f"Request: {method} {path} from {client[0]} (authenticated={bool(api_key)})")

        await self.app(scope, receive, send)

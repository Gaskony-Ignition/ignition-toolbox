"""
Authentication API Router

Provides endpoints for:
- API key management
- Role management
- Audit log viewing
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ignition_toolkit.auth.api_keys import get_api_key_manager
from ignition_toolkit.auth.rbac import Permission, get_rbac_manager
from ignition_toolkit.auth.audit import AuditEventType, get_audit_logger
from ignition_toolkit.auth.middleware import CurrentUser, require_auth, require_permission, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response Models

class CreateAPIKeyRequest(BaseModel):
    """Request to create an API key"""
    name: str = Field(..., min_length=1, max_length=100, description="Key name")
    role: str = Field(default="user", description="Role: admin, user, readonly, executor")
    scopes: list[str] | None = Field(default=None, description="Specific permission scopes")
    expires_in_days: int | None = Field(default=None, ge=1, le=365, description="Days until expiration")


class UpdateAPIKeyRequest(BaseModel):
    """Request to update an API key"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None)
    scopes: list[str] | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class CreateRoleRequest(BaseModel):
    """Request to create a custom role"""
    name: str = Field(..., min_length=1, max_length=50, description="Role name")
    description: str = Field(..., description="Role description")
    permissions: list[str] = Field(default_factory=list, description="Permission names")


# API Key Endpoints

@router.post("/keys")
async def create_api_key(
    request: CreateAPIKeyRequest,
    user: CurrentUser = Depends(require_permission(Permission.APIKEY_WRITE)),
):
    """
    Create a new API key

    Returns the raw key (shown only once) and key metadata.
    """
    manager = get_api_key_manager()

    raw_key, api_key = manager.create_key(
        name=request.name,
        user_id=user.api_key.user_id if user.api_key else None,
        role=request.role,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days,
    )

    # Audit log
    audit = get_audit_logger()
    audit.log(
        event_type=AuditEventType.AUTH_KEY_CREATED,
        user_id=user.api_key.user_id if user.api_key else None,
        api_key_id=user.api_key.id if user.api_key else None,
        ip_address=user.ip_address,
        resource_type="api_key",
        resource_id=api_key.id,
        details={"name": request.name, "role": request.role},
    )

    return {
        "success": True,
        "message": "API key created. Save the key - it won't be shown again.",
        "key": raw_key,  # Only shown once!
        "api_key": api_key.to_dict(),
    }


@router.get("/keys")
async def list_api_keys(
    user: CurrentUser = Depends(require_permission(Permission.APIKEY_READ)),
):
    """
    List API keys

    Admins see all keys, users see only their own.
    """
    manager = get_api_key_manager()

    # Admins see all, others see only their own
    if user.role == "admin":
        keys = manager.list_keys()
    else:
        user_id = user.api_key.user_id if user.api_key else None
        keys = manager.list_keys(user_id=user_id)

    return {
        "keys": [k.to_dict() for k in keys],
        "count": len(keys),
    }


@router.get("/keys/{key_id}")
async def get_api_key(
    key_id: str,
    user: CurrentUser = Depends(require_permission(Permission.APIKEY_READ)),
):
    """Get API key details"""
    manager = get_api_key_manager()
    api_key = manager.get_key(key_id)

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Non-admins can only view their own keys
    if user.role != "admin":
        if api_key.user_id != (user.api_key.user_id if user.api_key else None):
            raise HTTPException(status_code=403, detail="Access denied")

    return api_key.to_dict()


@router.put("/keys/{key_id}")
async def update_api_key(
    key_id: str,
    request: UpdateAPIKeyRequest,
    user: CurrentUser = Depends(require_permission(Permission.APIKEY_WRITE)),
):
    """Update an API key"""
    manager = get_api_key_manager()

    # Check key exists
    api_key = manager.get_key(key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Non-admins can only update their own keys
    if user.role != "admin":
        if api_key.user_id != (user.api_key.user_id if user.api_key else None):
            raise HTTPException(status_code=403, detail="Access denied")

    updated = manager.update_key(
        key_id=key_id,
        name=request.name,
        role=request.role,
        scopes=request.scopes,
        is_active=request.is_active,
    )

    return {
        "success": True,
        "api_key": updated.to_dict() if updated else None,
    }


@router.delete("/keys/{key_id}")
async def delete_api_key(
    key_id: str,
    user: CurrentUser = Depends(require_permission(Permission.APIKEY_DELETE)),
):
    """Delete an API key"""
    manager = get_api_key_manager()

    # Check key exists
    api_key = manager.get_key(key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Non-admins can only delete their own keys
    if user.role != "admin":
        if api_key.user_id != (user.api_key.user_id if user.api_key else None):
            raise HTTPException(status_code=403, detail="Access denied")

    deleted = manager.delete_key(key_id)

    # Audit log
    audit = get_audit_logger()
    audit.log(
        event_type=AuditEventType.AUTH_KEY_REVOKED,
        user_id=user.api_key.user_id if user.api_key else None,
        api_key_id=user.api_key.id if user.api_key else None,
        ip_address=user.ip_address,
        resource_type="api_key",
        resource_id=key_id,
    )

    return {"success": deleted}


# Role Endpoints

@router.get("/roles")
async def list_roles(
    user: CurrentUser = Depends(require_auth),
):
    """List all available roles"""
    rbac = get_rbac_manager()
    roles = rbac.list_roles()
    return {
        "roles": [r.to_dict() for r in roles],
        "count": len(roles),
    }


@router.get("/roles/{role_name}")
async def get_role(
    role_name: str,
    user: CurrentUser = Depends(require_auth),
):
    """Get role details including permissions"""
    rbac = get_rbac_manager()
    role = rbac.get_role(role_name)

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    return role.to_dict()


@router.post("/roles")
async def create_role(
    request: CreateRoleRequest,
    user: CurrentUser = Depends(require_role("admin")),
):
    """Create a custom role (admin only)"""
    rbac = get_rbac_manager()

    # Convert permission strings to Permission enums
    permissions = []
    for perm_str in request.permissions:
        try:
            perm = Permission(perm_str)
            permissions.append(perm)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid permission: {perm_str}"
            )

    try:
        role = rbac.create_role(
            name=request.name,
            description=request.description,
            permissions=permissions,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "role": role.to_dict(),
    }


@router.delete("/roles/{role_name}")
async def delete_role(
    role_name: str,
    user: CurrentUser = Depends(require_role("admin")),
):
    """Delete a custom role (admin only)"""
    rbac = get_rbac_manager()

    try:
        deleted = rbac.delete_role(role_name)
        if not deleted:
            raise HTTPException(status_code=404, detail="Role not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"success": True}


# Audit Log Endpoints

@router.get("/audit")
async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    event_type: str | None = None,
    user_id: str | None = None,
    success: bool | None = None,
    user: CurrentUser = Depends(require_role("admin")),
):
    """
    Get audit logs (admin only)

    Supports filtering by event type, user, and success status.
    """
    audit = get_audit_logger()

    # Convert event_type string to enum if provided
    event_type_enum = None
    if event_type:
        try:
            event_type_enum = AuditEventType(event_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type: {event_type}"
            )

    events = audit.get_events(
        limit=limit,
        offset=offset,
        event_type=event_type_enum,
        user_id=user_id,
        success=success,
    )

    return {
        "events": [e.to_dict() for e in events],
        "count": len(events),
    }


@router.get("/audit/stats")
async def get_audit_stats(
    user: CurrentUser = Depends(require_role("admin")),
):
    """Get audit log statistics (admin only)"""
    audit = get_audit_logger()
    return audit.get_stats()


# Current User Endpoint

@router.get("/me")
async def get_current_user_info(
    user: CurrentUser = Depends(require_auth),
):
    """Get information about the currently authenticated user"""
    rbac = get_rbac_manager()
    permissions = rbac.get_permissions_for_role(user.role)

    return {
        "is_authenticated": user.is_authenticated,
        "role": user.role,
        "scopes": user.scopes,
        "permissions": [p.value for p in permissions],
        "api_key": user.api_key.to_dict() if user.api_key else None,
    }


@router.get("/permissions")
async def list_permissions(
    user: CurrentUser = Depends(require_auth),
):
    """List all available permissions"""
    return {
        "permissions": [
            {"name": p.name, "value": p.value}
            for p in Permission
        ]
    }

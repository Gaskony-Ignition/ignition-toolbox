"""
Authentication and Authorization module

Provides:
- API key authentication
- Role-based access control (RBAC)
- User session management
- Audit logging
"""

from ignition_toolkit.auth.api_keys import APIKeyManager, APIKey
from ignition_toolkit.auth.rbac import Role, Permission, RBACManager
from ignition_toolkit.auth.audit import AuditLogger, AuditEvent
from ignition_toolkit.auth.middleware import AuthMiddleware, get_current_user

__all__ = [
    "APIKeyManager",
    "APIKey",
    "Role",
    "Permission",
    "RBACManager",
    "AuditLogger",
    "AuditEvent",
    "AuthMiddleware",
    "get_current_user",
]

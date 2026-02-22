"""
Authentication and Authorization module

Provides:
- API key authentication
- Role-based access control (RBAC)
- User session management
- Audit logging
"""

from ignition_toolkit.auth.api_keys import APIKey, APIKeyManager
from ignition_toolkit.auth.audit import AuditEvent, AuditLogger
from ignition_toolkit.auth.middleware import AuthMiddleware, get_current_user
from ignition_toolkit.auth.rbac import Permission, RBACManager, Role

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

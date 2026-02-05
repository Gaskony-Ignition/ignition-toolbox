"""
Role-Based Access Control (RBAC)

Defines roles, permissions, and access control logic.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Available permissions"""
    # Playbook permissions
    PLAYBOOK_READ = "playbook:read"
    PLAYBOOK_WRITE = "playbook:write"
    PLAYBOOK_EXECUTE = "playbook:execute"
    PLAYBOOK_DELETE = "playbook:delete"

    # Execution permissions
    EXECUTION_READ = "execution:read"
    EXECUTION_WRITE = "execution:write"
    EXECUTION_CANCEL = "execution:cancel"

    # Credential permissions
    CREDENTIAL_READ = "credential:read"
    CREDENTIAL_WRITE = "credential:write"
    CREDENTIAL_DELETE = "credential:delete"

    # Schedule permissions
    SCHEDULE_READ = "schedule:read"
    SCHEDULE_WRITE = "schedule:write"
    SCHEDULE_DELETE = "schedule:delete"

    # System permissions
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_ADMIN = "system:admin"

    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"

    # API key management
    APIKEY_READ = "apikey:read"
    APIKEY_WRITE = "apikey:write"
    APIKEY_DELETE = "apikey:delete"


@dataclass
class Role:
    """Defines a role with associated permissions"""
    name: str
    description: str
    permissions: set[Permission] = field(default_factory=set)
    is_system: bool = False  # System roles cannot be deleted

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a permission"""
        return permission in self.permissions

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "permissions": [p.value for p in self.permissions],
            "is_system": self.is_system,
        }


# Predefined system roles
ADMIN_ROLE = Role(
    name="admin",
    description="Full system access",
    permissions=set(Permission),  # All permissions
    is_system=True,
)

USER_ROLE = Role(
    name="user",
    description="Standard user access",
    permissions={
        Permission.PLAYBOOK_READ,
        Permission.PLAYBOOK_WRITE,
        Permission.PLAYBOOK_EXECUTE,
        Permission.EXECUTION_READ,
        Permission.EXECUTION_WRITE,
        Permission.EXECUTION_CANCEL,
        Permission.CREDENTIAL_READ,
        Permission.CREDENTIAL_WRITE,
        Permission.SCHEDULE_READ,
        Permission.SCHEDULE_WRITE,
        Permission.SYSTEM_READ,
        Permission.APIKEY_READ,
    },
    is_system=True,
)

READONLY_ROLE = Role(
    name="readonly",
    description="Read-only access",
    permissions={
        Permission.PLAYBOOK_READ,
        Permission.EXECUTION_READ,
        Permission.CREDENTIAL_READ,
        Permission.SCHEDULE_READ,
        Permission.SYSTEM_READ,
    },
    is_system=True,
)

EXECUTOR_ROLE = Role(
    name="executor",
    description="Can only execute playbooks",
    permissions={
        Permission.PLAYBOOK_READ,
        Permission.PLAYBOOK_EXECUTE,
        Permission.EXECUTION_READ,
        Permission.EXECUTION_WRITE,
        Permission.CREDENTIAL_READ,
    },
    is_system=True,
)


class RBACManager:
    """
    Role-Based Access Control Manager

    Manages roles and permission checks.

    Example:
        rbac = RBACManager()

        # Check permission
        if rbac.check_permission("user", Permission.PLAYBOOK_EXECUTE):
            # Allow execution
            pass

        # Create custom role
        rbac.create_role(
            name="qa_tester",
            description="QA testing role",
            permissions=[Permission.PLAYBOOK_READ, Permission.PLAYBOOK_EXECUTE]
        )
    """

    def __init__(self):
        """Initialize RBAC manager with default roles"""
        self._roles: dict[str, Role] = {
            "admin": ADMIN_ROLE,
            "user": USER_ROLE,
            "readonly": READONLY_ROLE,
            "executor": EXECUTOR_ROLE,
        }
        logger.info("RBACManager initialized with default roles")

    def check_permission(
        self,
        role_name: str,
        permission: Permission,
        scopes: list[str] | None = None,
    ) -> bool:
        """
        Check if a role has a permission

        Args:
            role_name: Name of the role
            permission: Permission to check
            scopes: Additional scopes that grant permission

        Returns:
            True if allowed, False otherwise
        """
        # Check role permissions
        role = self._roles.get(role_name)
        if role and role.has_permission(permission):
            return True

        # Check specific scopes
        if scopes:
            if permission.value in scopes or "*" in scopes:
                return True

        return False

    def get_role(self, role_name: str) -> Role | None:
        """Get a role by name"""
        return self._roles.get(role_name)

    def list_roles(self) -> list[Role]:
        """List all roles"""
        return list(self._roles.values())

    def create_role(
        self,
        name: str,
        description: str,
        permissions: list[Permission] | None = None,
    ) -> Role:
        """
        Create a custom role

        Args:
            name: Role name (must be unique)
            description: Role description
            permissions: List of permissions

        Returns:
            Created Role

        Raises:
            ValueError if role name already exists
        """
        if name in self._roles:
            raise ValueError(f"Role '{name}' already exists")

        role = Role(
            name=name,
            description=description,
            permissions=set(permissions) if permissions else set(),
            is_system=False,
        )

        self._roles[name] = role
        logger.info(f"Created role '{name}' with {len(role.permissions)} permissions")
        return role

    def update_role(
        self,
        name: str,
        description: str | None = None,
        permissions: list[Permission] | None = None,
    ) -> Role | None:
        """
        Update a role

        Args:
            name: Role name
            description: New description (optional)
            permissions: New permissions (optional)

        Returns:
            Updated Role or None if not found

        Raises:
            ValueError if trying to modify system role permissions
        """
        role = self._roles.get(name)
        if not role:
            return None

        if role.is_system and permissions is not None:
            raise ValueError(f"Cannot modify permissions of system role '{name}'")

        if description is not None:
            role.description = description

        if permissions is not None:
            role.permissions = set(permissions)

        logger.info(f"Updated role '{name}'")
        return role

    def delete_role(self, name: str) -> bool:
        """
        Delete a role

        Args:
            name: Role name

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError if trying to delete system role
        """
        role = self._roles.get(name)
        if not role:
            return False

        if role.is_system:
            raise ValueError(f"Cannot delete system role '{name}'")

        del self._roles[name]
        logger.info(f"Deleted role '{name}'")
        return True

    def get_permissions_for_role(self, role_name: str) -> list[Permission]:
        """Get all permissions for a role"""
        role = self._roles.get(role_name)
        if not role:
            return []
        return list(role.permissions)


# Global instance
_rbac_manager: RBACManager | None = None


def get_rbac_manager() -> RBACManager:
    """Get the global RBAC manager"""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager

"""
Tests for Role-Based Access Control (RBAC).

Tests Role dataclass, Permission enum, predefined system roles,
and RBACManager behaviour.
"""

import pytest
from ignition_toolkit.auth.rbac import (
    Permission,
    Role,
    RBACManager,
    ADMIN_ROLE,
    USER_ROLE,
    READONLY_ROLE,
    EXECUTOR_ROLE,
    get_rbac_manager,
)


class TestPermissionEnum:
    def test_permission_enum_has_expected_values(self):
        """Permission enum contains the expected string values."""
        assert Permission.PLAYBOOK_READ.value == "playbook:read"
        assert Permission.PLAYBOOK_WRITE.value == "playbook:write"
        assert Permission.PLAYBOOK_EXECUTE.value == "playbook:execute"
        assert Permission.PLAYBOOK_DELETE.value == "playbook:delete"

    def test_execution_permissions_exist(self):
        """Execution-related permissions are present in the enum."""
        assert Permission.EXECUTION_READ.value == "execution:read"
        assert Permission.EXECUTION_WRITE.value == "execution:write"
        assert Permission.EXECUTION_CANCEL.value == "execution:cancel"

    def test_credential_permissions_exist(self):
        """Credential-related permissions are present in the enum."""
        assert Permission.CREDENTIAL_READ.value == "credential:read"
        assert Permission.CREDENTIAL_WRITE.value == "credential:write"
        assert Permission.CREDENTIAL_DELETE.value == "credential:delete"

    def test_system_permissions_exist(self):
        """System-level permissions are present in the enum."""
        assert Permission.SYSTEM_READ.value == "system:read"
        assert Permission.SYSTEM_WRITE.value == "system:write"
        assert Permission.SYSTEM_ADMIN.value == "system:admin"

    def test_user_management_permissions_exist(self):
        """User management permissions are present in the enum."""
        assert Permission.USER_READ.value == "user:read"
        assert Permission.USER_WRITE.value == "user:write"
        assert Permission.USER_DELETE.value == "user:delete"

    def test_apikey_permissions_exist(self):
        """API key permissions are present in the enum."""
        assert Permission.APIKEY_READ.value == "apikey:read"
        assert Permission.APIKEY_WRITE.value == "apikey:write"
        assert Permission.APIKEY_DELETE.value == "apikey:delete"


class TestRoleDataclass:
    def test_role_can_be_instantiated(self):
        """Role dataclass can be created with name, description, and permissions."""
        role = Role(
            name="test_role",
            description="A test role",
            permissions={Permission.PLAYBOOK_READ},
        )
        assert role.name == "test_role"
        assert role.description == "A test role"
        assert role.is_system is False

    def test_role_has_permission_returns_true_for_granted(self):
        """Role.has_permission() returns True when the permission is in the set."""
        role = Role(
            name="r",
            description="d",
            permissions={Permission.PLAYBOOK_READ, Permission.EXECUTION_READ},
        )
        assert role.has_permission(Permission.PLAYBOOK_READ) is True
        assert role.has_permission(Permission.EXECUTION_READ) is True

    def test_role_has_permission_returns_false_for_missing(self):
        """Role.has_permission() returns False when the permission is not granted."""
        role = Role(
            name="r",
            description="d",
            permissions={Permission.PLAYBOOK_READ},
        )
        assert role.has_permission(Permission.PLAYBOOK_DELETE) is False
        assert role.has_permission(Permission.SYSTEM_ADMIN) is False

    def test_role_to_dict_contains_expected_keys(self):
        """Role.to_dict() returns a dict with name, description, permissions, is_system."""
        role = Role(
            name="my_role",
            description="desc",
            permissions={Permission.CREDENTIAL_READ},
            is_system=True,
        )
        d = role.to_dict()
        assert d["name"] == "my_role"
        assert d["description"] == "desc"
        assert d["is_system"] is True
        assert isinstance(d["permissions"], list)
        assert Permission.CREDENTIAL_READ.value in d["permissions"]

    def test_role_empty_permissions_by_default(self):
        """Role with no permissions has an empty permissions set."""
        role = Role(name="empty", description="no perms")
        assert len(role.permissions) == 0
        assert role.has_permission(Permission.PLAYBOOK_READ) is False


class TestPredefinedRoles:
    def test_admin_role_has_all_permissions(self):
        """ADMIN_ROLE has every permission defined in the Permission enum."""
        all_permissions = set(Permission)
        assert ADMIN_ROLE.permissions == all_permissions
        assert ADMIN_ROLE.is_system is True

    def test_admin_role_name(self):
        """ADMIN_ROLE has the expected name."""
        assert ADMIN_ROLE.name == "admin"

    def test_user_role_has_expected_permissions(self):
        """USER_ROLE has read/write/execute permissions but not admin or delete."""
        assert Permission.PLAYBOOK_READ in USER_ROLE.permissions
        assert Permission.PLAYBOOK_EXECUTE in USER_ROLE.permissions
        assert Permission.PLAYBOOK_WRITE in USER_ROLE.permissions
        assert Permission.EXECUTION_CANCEL in USER_ROLE.permissions
        # Users should NOT have system admin
        assert Permission.SYSTEM_ADMIN not in USER_ROLE.permissions
        assert USER_ROLE.is_system is True

    def test_readonly_role_has_only_read_permissions(self):
        """READONLY_ROLE contains only read-type permissions."""
        for perm in READONLY_ROLE.permissions:
            assert perm.value.endswith(":read"), (
                f"READONLY_ROLE should not have non-read permission: {perm}"
            )
        assert READONLY_ROLE.is_system is True

    def test_executor_role_can_execute_but_not_write_playbooks(self):
        """EXECUTOR_ROLE can execute and read playbooks but cannot write them."""
        assert Permission.PLAYBOOK_EXECUTE in EXECUTOR_ROLE.permissions
        assert Permission.PLAYBOOK_READ in EXECUTOR_ROLE.permissions
        assert Permission.PLAYBOOK_WRITE not in EXECUTOR_ROLE.permissions
        assert Permission.PLAYBOOK_DELETE not in EXECUTOR_ROLE.permissions
        assert EXECUTOR_ROLE.is_system is True


class TestRBACManager:
    def setup_method(self):
        """Create a fresh RBACManager for each test."""
        self.rbac = RBACManager()

    def test_rbac_manager_initialises_with_four_default_roles(self):
        """RBACManager starts with admin, user, readonly, and executor roles."""
        roles = {r.name for r in self.rbac.list_roles()}
        assert "admin" in roles
        assert "user" in roles
        assert "readonly" in roles
        assert "executor" in roles

    def test_check_permission_admin_has_all(self):
        """check_permission() returns True for every permission with admin role."""
        for perm in Permission:
            assert self.rbac.check_permission("admin", perm) is True

    def test_check_permission_readonly_only_reads(self):
        """check_permission() returns True for read permissions, False for write."""
        assert self.rbac.check_permission("readonly", Permission.PLAYBOOK_READ) is True
        assert self.rbac.check_permission("readonly", Permission.EXECUTION_READ) is True
        assert self.rbac.check_permission("readonly", Permission.PLAYBOOK_WRITE) is False
        assert self.rbac.check_permission("readonly", Permission.PLAYBOOK_DELETE) is False
        assert self.rbac.check_permission("readonly", Permission.SYSTEM_ADMIN) is False

    def test_check_permission_executor_can_execute_not_delete(self):
        """check_permission() executor can execute but not delete playbooks."""
        assert self.rbac.check_permission("executor", Permission.PLAYBOOK_EXECUTE) is True
        assert self.rbac.check_permission("executor", Permission.PLAYBOOK_DELETE) is False

    def test_check_permission_unknown_role_returns_false(self):
        """check_permission() returns False for a role that does not exist."""
        assert self.rbac.check_permission("nonexistent_role", Permission.PLAYBOOK_READ) is False

    def test_check_permission_with_wildcard_scope(self):
        """check_permission() returns True when '*' is in the scopes list."""
        # Unknown role but wildcard scope grants all
        assert self.rbac.check_permission(
            "nonexistent_role", Permission.SYSTEM_ADMIN, scopes=["*"]
        ) is True

    def test_check_permission_with_exact_scope(self):
        """check_permission() returns True when the exact permission value is in scopes."""
        assert self.rbac.check_permission(
            "nonexistent_role",
            Permission.PLAYBOOK_EXECUTE,
            scopes=["playbook:execute"],
        ) is True

    def test_get_role_returns_correct_role(self):
        """get_role() returns the Role object for a known role name."""
        role = self.rbac.get_role("admin")
        assert role is not None
        assert role.name == "admin"

    def test_get_role_returns_none_for_unknown(self):
        """get_role() returns None for an unknown role name."""
        assert self.rbac.get_role("no_such_role") is None

    def test_create_role_adds_custom_role(self):
        """create_role() adds a new non-system role that can be retrieved."""
        self.rbac.create_role(
            name="qa_tester",
            description="QA testing role",
            permissions=[Permission.PLAYBOOK_READ, Permission.PLAYBOOK_EXECUTE],
        )
        role = self.rbac.get_role("qa_tester")
        assert role is not None
        assert role.name == "qa_tester"
        assert role.is_system is False
        assert Permission.PLAYBOOK_READ in role.permissions
        assert Permission.PLAYBOOK_EXECUTE in role.permissions

    def test_create_role_raises_on_duplicate_name(self):
        """create_role() raises ValueError when name already exists."""
        with pytest.raises(ValueError, match="already exists"):
            self.rbac.create_role(name="admin", description="duplicate attempt")

    def test_delete_role_removes_custom_role(self):
        """delete_role() successfully removes a non-system role."""
        self.rbac.create_role(name="temp_role", description="temp")
        result = self.rbac.delete_role("temp_role")
        assert result is True
        assert self.rbac.get_role("temp_role") is None

    def test_delete_role_raises_for_system_role(self):
        """delete_role() raises ValueError when trying to delete a system role."""
        with pytest.raises(ValueError, match="system role"):
            self.rbac.delete_role("admin")

    def test_delete_role_returns_false_for_unknown(self):
        """delete_role() returns False when the role does not exist."""
        result = self.rbac.delete_role("no_such_role")
        assert result is False

    def test_update_role_description(self):
        """update_role() can change a system role's description."""
        result = self.rbac.update_role("user", description="Updated description")
        assert result is not None
        assert result.description == "Updated description"

    def test_update_system_role_permissions_raises(self):
        """update_role() raises ValueError when trying to change system role permissions."""
        with pytest.raises(ValueError, match="Cannot modify permissions"):
            self.rbac.update_role("admin", permissions=[Permission.PLAYBOOK_READ])

    def test_get_permissions_for_role_returns_list(self):
        """get_permissions_for_role() returns a list of Permission values."""
        perms = self.rbac.get_permissions_for_role("readonly")
        assert isinstance(perms, list)
        assert len(perms) > 0
        for p in perms:
            assert isinstance(p, Permission)

    def test_get_permissions_for_unknown_role_returns_empty(self):
        """get_permissions_for_role() returns an empty list for unknown roles."""
        perms = self.rbac.get_permissions_for_role("unknown")
        assert perms == []


class TestGetRBACManagerSingleton:
    def test_get_rbac_manager_returns_instance(self):
        """get_rbac_manager() returns an RBACManager instance."""
        manager = get_rbac_manager()
        assert isinstance(manager, RBACManager)

    def test_get_rbac_manager_returns_same_instance(self):
        """get_rbac_manager() returns the same singleton object on repeated calls."""
        m1 = get_rbac_manager()
        m2 = get_rbac_manager()
        assert m1 is m2

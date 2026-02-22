"""
Tests for authentication / API key management API endpoints.

Tests list, get, create, update, and delete operations.
Because every endpoint uses FastAPI Depends() for auth, we call the
underlying business logic (manager + router functions) with manually-
constructed CurrentUser objects rather than going through the HTTP stack.

Pattern: patch get_api_key_manager / get_rbac_manager / get_audit_logger
at the router module level, then call the endpoint function directly with
a pre-built CurrentUser injected as the ``user`` keyword argument.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from ignition_toolkit.auth.middleware import CurrentUser
from ignition_toolkit.auth.rbac import Permission


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin_user() -> CurrentUser:
    """A fully-authenticated admin CurrentUser."""
    mock_key = MagicMock()
    mock_key.user_id = "user-123"
    mock_key.id = "key-abc"
    return CurrentUser(
        api_key=mock_key,
        is_authenticated=True,
        role="admin",
        scopes=[],
        ip_address="127.0.0.1",
    )


def _regular_user(user_id: str = "user-456") -> CurrentUser:
    """A regular (non-admin) authenticated CurrentUser."""
    mock_key = MagicMock()
    mock_key.user_id = user_id
    mock_key.id = "key-def"
    return CurrentUser(
        api_key=mock_key,
        is_authenticated=True,
        role="user",
        scopes=[],
        ip_address="127.0.0.1",
    )


def _make_api_key_mock(key_id: str = "key-001", name: str = "Test Key", role: str = "user",
                       user_id: str = "user-123") -> MagicMock:
    """Build a mock APIKey object."""
    api_key = MagicMock()
    api_key.id = key_id
    api_key.name = name
    api_key.role = role
    api_key.user_id = user_id
    api_key.scopes = []
    api_key.is_active = True
    api_key.to_dict.return_value = {
        "id": key_id,
        "name": name,
        "role": role,
        "user_id": user_id,
        "scopes": [],
        "is_active": True,
    }
    return api_key


# ---------------------------------------------------------------------------
# list_api_keys
# ---------------------------------------------------------------------------

class TestListAPIKeys:
    def test_list_api_keys_admin_sees_all(self):
        """Admin user gets all keys returned."""
        from ignition_toolkit.api.routers.auth import list_api_keys

        key1 = _make_api_key_mock("k1", "Key One")
        key2 = _make_api_key_mock("k2", "Key Two")

        mock_manager = MagicMock()
        mock_manager.list_keys.return_value = [key1, key2]

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            result = asyncio.run(list_api_keys(user=_admin_user()))

        assert "keys" in result
        assert result["count"] == 2
        # Admin calls list_keys() with no user_id filter
        mock_manager.list_keys.assert_called_once_with()

    def test_list_api_keys_regular_user_filtered(self):
        """Non-admin user only sees their own keys."""
        from ignition_toolkit.api.routers.auth import list_api_keys

        user = _regular_user(user_id="user-456")
        own_key = _make_api_key_mock("k3", "My Key", user_id="user-456")

        mock_manager = MagicMock()
        mock_manager.list_keys.return_value = [own_key]

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            result = asyncio.run(list_api_keys(user=user))

        assert result["count"] == 1
        mock_manager.list_keys.assert_called_once_with(user_id="user-456")

    def test_list_api_keys_returns_empty_list(self):
        """list_api_keys returns empty list when no keys exist."""
        from ignition_toolkit.api.routers.auth import list_api_keys

        mock_manager = MagicMock()
        mock_manager.list_keys.return_value = []

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            result = asyncio.run(list_api_keys(user=_admin_user()))

        assert result["keys"] == []
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# create_api_key
# ---------------------------------------------------------------------------

class TestCreateAPIKey:
    def test_create_api_key_returns_key_and_metadata(self):
        """POST /auth/keys returns raw key + api_key dict on success."""
        from ignition_toolkit.api.routers.auth import create_api_key, CreateAPIKeyRequest

        mock_api_key = _make_api_key_mock("new-key-id", "CI Key", role="user")
        mock_manager = MagicMock()
        mock_manager.create_key.return_value = ("itk_rawsecretvalue", mock_api_key)

        mock_audit = MagicMock()
        mock_audit.log.return_value = None

        request = CreateAPIKeyRequest(name="CI Key", role="user")

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager), \
             patch("ignition_toolkit.api.routers.auth.get_audit_logger", return_value=mock_audit):
            result = asyncio.run(create_api_key(request=request, user=_admin_user()))

        assert result["success"] is True
        assert result["key"] == "itk_rawsecretvalue"
        assert "api_key" in result
        assert result["api_key"]["name"] == "CI Key"

    def test_create_api_key_with_expiry(self):
        """POST /auth/keys accepts expires_in_days and passes it to manager."""
        from ignition_toolkit.api.routers.auth import create_api_key, CreateAPIKeyRequest

        mock_api_key = _make_api_key_mock("exp-key", "Expiring Key")
        mock_manager = MagicMock()
        mock_manager.create_key.return_value = ("itk_expkey", mock_api_key)

        mock_audit = MagicMock()

        request = CreateAPIKeyRequest(name="Expiring Key", role="readonly", expires_in_days=30)

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager), \
             patch("ignition_toolkit.api.routers.auth.get_audit_logger", return_value=mock_audit):
            result = asyncio.run(create_api_key(request=request, user=_admin_user()))

        call_kwargs = mock_manager.create_key.call_args.kwargs
        assert call_kwargs["expires_in_days"] == 30

    def test_create_api_key_name_required(self):
        """CreateAPIKeyRequest raises ValidationError when name is empty."""
        from ignition_toolkit.api.routers.auth import CreateAPIKeyRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CreateAPIKeyRequest(name="", role="user")

    def test_create_api_key_expires_in_days_range(self):
        """expires_in_days must be 1-365; values outside raise ValidationError."""
        from ignition_toolkit.api.routers.auth import CreateAPIKeyRequest
        from pydantic import ValidationError

        # Too small
        with pytest.raises(ValidationError):
            CreateAPIKeyRequest(name="K", expires_in_days=0)

        # Too large
        with pytest.raises(ValidationError):
            CreateAPIKeyRequest(name="K", expires_in_days=366)

        # Boundary values should be accepted
        valid_min = CreateAPIKeyRequest(name="K", expires_in_days=1)
        valid_max = CreateAPIKeyRequest(name="K", expires_in_days=365)
        assert valid_min.expires_in_days == 1
        assert valid_max.expires_in_days == 365


# ---------------------------------------------------------------------------
# get_api_key
# ---------------------------------------------------------------------------

class TestGetAPIKey:
    def test_get_api_key_returns_key_dict(self):
        """GET /auth/keys/{id} returns key data when found."""
        from ignition_toolkit.api.routers.auth import get_api_key

        existing = _make_api_key_mock("k-found", "Found Key", user_id="user-123")
        mock_manager = MagicMock()
        mock_manager.get_key.return_value = existing

        user = _admin_user()

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            result = asyncio.run(get_api_key(key_id="k-found", user=user))

        assert result["id"] == "k-found"
        assert result["name"] == "Found Key"

    def test_get_api_key_404_for_unknown_id(self):
        """GET /auth/keys/{id} raises 404 when key doesn't exist."""
        from ignition_toolkit.api.routers.auth import get_api_key

        mock_manager = MagicMock()
        mock_manager.get_key.return_value = None

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_api_key(key_id="nonexistent", user=_admin_user()))

        assert exc_info.value.status_code == 404

    def test_get_api_key_403_for_other_users_key(self):
        """Non-admin cannot view another user's key — raises 403."""
        from ignition_toolkit.api.routers.auth import get_api_key

        other_key = _make_api_key_mock("k-other", "Other Key", user_id="other-user-789")
        mock_manager = MagicMock()
        mock_manager.get_key.return_value = other_key

        # Regular user whose user_id does NOT match the key's user_id
        regular = _regular_user(user_id="user-456")

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_api_key(key_id="k-other", user=regular))

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# delete_api_key
# ---------------------------------------------------------------------------

class TestDeleteAPIKey:
    def test_delete_api_key_succeeds(self):
        """DELETE /auth/keys/{id} returns success when key exists."""
        from ignition_toolkit.api.routers.auth import delete_api_key

        existing = _make_api_key_mock("k-del", "Delete Me", user_id="user-123")
        mock_manager = MagicMock()
        mock_manager.get_key.return_value = existing
        mock_manager.delete_key.return_value = True

        mock_audit = MagicMock()

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager), \
             patch("ignition_toolkit.api.routers.auth.get_audit_logger", return_value=mock_audit):
            result = asyncio.run(delete_api_key(key_id="k-del", user=_admin_user()))

        assert result["success"] is True
        mock_manager.delete_key.assert_called_once_with("k-del")

    def test_delete_api_key_404_for_unknown_id(self):
        """DELETE /auth/keys/{id} raises 404 when key doesn't exist."""
        from ignition_toolkit.api.routers.auth import delete_api_key

        mock_manager = MagicMock()
        mock_manager.get_key.return_value = None

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_api_key(key_id="ghost-key", user=_admin_user()))

        assert exc_info.value.status_code == 404

    def test_delete_api_key_403_for_other_users_key(self):
        """Non-admin cannot delete another user's key — raises 403."""
        from ignition_toolkit.api.routers.auth import delete_api_key

        other_key = _make_api_key_mock("k-other2", "Not Mine", user_id="owner-999")
        mock_manager = MagicMock()
        mock_manager.get_key.return_value = other_key

        regular = _regular_user(user_id="user-456")

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_api_key(key_id="k-other2", user=regular))

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# update_api_key
# ---------------------------------------------------------------------------

class TestUpdateAPIKey:
    def test_update_api_key_returns_updated_key(self):
        """PUT /auth/keys/{id} returns updated key data."""
        from ignition_toolkit.api.routers.auth import update_api_key, UpdateAPIKeyRequest

        existing = _make_api_key_mock("k-upd", "Old Name", user_id="user-123")
        updated = _make_api_key_mock("k-upd", "New Name", user_id="user-123")

        mock_manager = MagicMock()
        mock_manager.get_key.return_value = existing
        mock_manager.update_key.return_value = updated

        request = UpdateAPIKeyRequest(name="New Name")

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            result = asyncio.run(update_api_key(key_id="k-upd", request=request, user=_admin_user()))

        assert result["success"] is True
        assert result["api_key"]["name"] == "New Name"

    def test_update_api_key_404_when_not_found(self):
        """PUT /auth/keys/{id} raises 404 for unknown key."""
        from ignition_toolkit.api.routers.auth import update_api_key, UpdateAPIKeyRequest

        mock_manager = MagicMock()
        mock_manager.get_key.return_value = None

        request = UpdateAPIKeyRequest(name="Anything")

        with patch("ignition_toolkit.api.routers.auth.get_api_key_manager", return_value=mock_manager):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(update_api_key(key_id="missing", request=request, user=_admin_user()))

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# list_roles
# ---------------------------------------------------------------------------

class TestListRoles:
    def test_list_roles_returns_roles(self):
        """GET /auth/roles returns all roles."""
        from ignition_toolkit.api.routers.auth import list_roles

        mock_role = MagicMock()
        mock_role.to_dict.return_value = {"name": "admin", "description": "Administrator"}

        mock_rbac = MagicMock()
        mock_rbac.list_roles.return_value = [mock_role]

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            result = asyncio.run(list_roles(user=_admin_user()))

        assert "roles" in result
        assert result["count"] == 1
        assert result["roles"][0]["name"] == "admin"

    def test_list_roles_empty(self):
        """GET /auth/roles returns empty list when no roles defined."""
        from ignition_toolkit.api.routers.auth import list_roles

        mock_rbac = MagicMock()
        mock_rbac.list_roles.return_value = []

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            result = asyncio.run(list_roles(user=_admin_user()))

        assert result["roles"] == []
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# get_role
# ---------------------------------------------------------------------------

class TestGetRole:
    def test_get_role_returns_role_data(self):
        """GET /auth/roles/{name} returns role details."""
        from ignition_toolkit.api.routers.auth import get_role

        mock_role = MagicMock()
        mock_role.to_dict.return_value = {"name": "user", "description": "Regular user"}

        mock_rbac = MagicMock()
        mock_rbac.get_role.return_value = mock_role

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            result = asyncio.run(get_role(role_name="user", user=_admin_user()))

        assert result["name"] == "user"

    def test_get_role_404_for_unknown_role(self):
        """GET /auth/roles/{name} raises 404 for unknown role."""
        from ignition_toolkit.api.routers.auth import get_role

        mock_rbac = MagicMock()
        mock_rbac.get_role.return_value = None

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_role(role_name="nonexistent_role", user=_admin_user()))

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_role
# ---------------------------------------------------------------------------

class TestDeleteRole:
    def test_delete_role_succeeds(self):
        """DELETE /auth/roles/{name} returns success when role exists."""
        from ignition_toolkit.api.routers.auth import delete_role

        mock_rbac = MagicMock()
        mock_rbac.delete_role.return_value = True

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            result = asyncio.run(delete_role(role_name="custom_role", user=_admin_user()))

        assert result["success"] is True

    def test_delete_role_404_when_not_found(self):
        """DELETE /auth/roles/{name} raises 404 when role doesn't exist."""
        from ignition_toolkit.api.routers.auth import delete_role

        mock_rbac = MagicMock()
        mock_rbac.delete_role.return_value = False

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_role(role_name="ghost_role", user=_admin_user()))

        assert exc_info.value.status_code == 404

    def test_delete_role_400_for_system_role(self):
        """DELETE /auth/roles/{name} raises 400 when trying to delete a system role."""
        from ignition_toolkit.api.routers.auth import delete_role

        mock_rbac = MagicMock()
        mock_rbac.delete_role.side_effect = ValueError("Cannot delete system roles")

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_role(role_name="admin", user=_admin_user()))

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# create_role
# ---------------------------------------------------------------------------

class TestCreateRole:
    def test_create_role_succeeds(self):
        """POST /auth/roles creates a custom role and returns it."""
        from ignition_toolkit.api.routers.auth import create_role, CreateRoleRequest

        mock_role = MagicMock()
        mock_role.to_dict.return_value = {
            "name": "ci_runner",
            "description": "CI automation role",
            "permissions": [],
        }

        mock_rbac = MagicMock()
        mock_rbac.create_role.return_value = mock_role

        request = CreateRoleRequest(
            name="ci_runner",
            description="CI automation role",
            permissions=[],
        )

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            result = asyncio.run(create_role(request=request, user=_admin_user()))

        assert result["success"] is True
        assert result["role"]["name"] == "ci_runner"

    def test_create_role_400_for_invalid_permission(self):
        """POST /auth/roles raises 400 for an unrecognised permission string."""
        from ignition_toolkit.api.routers.auth import create_role, CreateRoleRequest

        mock_rbac = MagicMock()

        request = CreateRoleRequest(
            name="bad_role",
            description="Role with invalid perms",
            permissions=["totally:invalid:permission"],
        )

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(create_role(request=request, user=_admin_user()))

        assert exc_info.value.status_code == 400

    def test_create_role_400_for_duplicate_role(self):
        """POST /auth/roles raises 400 when role name already exists."""
        from ignition_toolkit.api.routers.auth import create_role, CreateRoleRequest

        mock_rbac = MagicMock()
        mock_rbac.create_role.side_effect = ValueError("Role already exists")

        request = CreateRoleRequest(
            name="existing_role",
            description="Duplicate",
            permissions=[],
        )

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(create_role(request=request, user=_admin_user()))

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# get_audit_logs
# ---------------------------------------------------------------------------

class TestGetAuditLogs:
    def test_get_audit_logs_returns_events(self):
        """GET /auth/audit returns events list."""
        from ignition_toolkit.api.routers.auth import get_audit_logs

        mock_event = MagicMock()
        mock_event.to_dict.return_value = {"event_type": "auth.login", "success": True}

        mock_audit = MagicMock()
        mock_audit.get_events.return_value = [mock_event]

        with patch("ignition_toolkit.api.routers.auth.get_audit_logger", return_value=mock_audit):
            result = asyncio.run(get_audit_logs(
                limit=100, offset=0, event_type=None, user_id=None, success=None,
                user=_admin_user(),
            ))

        assert "events" in result
        assert result["count"] == 1

    def test_get_audit_logs_400_for_invalid_event_type(self):
        """GET /auth/audit raises 400 for invalid event_type string."""
        from ignition_toolkit.api.routers.auth import get_audit_logs

        mock_audit = MagicMock()

        with patch("ignition_toolkit.api.routers.auth.get_audit_logger", return_value=mock_audit):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_audit_logs(
                    limit=100, offset=0, event_type="not.a.real.event",
                    user_id=None, success=None, user=_admin_user(),
                ))

        assert exc_info.value.status_code == 400

    def test_get_audit_logs_empty(self):
        """GET /auth/audit returns empty list when no events exist."""
        from ignition_toolkit.api.routers.auth import get_audit_logs

        mock_audit = MagicMock()
        mock_audit.get_events.return_value = []

        with patch("ignition_toolkit.api.routers.auth.get_audit_logger", return_value=mock_audit):
            result = asyncio.run(get_audit_logs(
                limit=100, offset=0, event_type=None, user_id=None, success=None,
                user=_admin_user(),
            ))

        assert result["events"] == []
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# list_permissions
# ---------------------------------------------------------------------------

class TestListPermissions:
    def test_list_permissions_returns_all_permissions(self):
        """GET /auth/permissions lists every Permission enum value."""
        from ignition_toolkit.api.routers.auth import list_permissions

        result = asyncio.run(list_permissions(user=_admin_user()))

        assert "permissions" in result
        assert len(result["permissions"]) == len(list(Permission))
        # Each entry has name and value
        first = result["permissions"][0]
        assert "name" in first
        assert "value" in first


# ---------------------------------------------------------------------------
# get_current_user_info
# ---------------------------------------------------------------------------

class TestGetCurrentUserInfo:
    def test_get_current_user_info_returns_user_data(self):
        """GET /auth/me returns info for authenticated user."""
        from ignition_toolkit.api.routers.auth import get_current_user_info

        mock_rbac = MagicMock()
        mock_rbac.get_permissions_for_role.return_value = [Permission.PLAYBOOK_READ]

        user = _admin_user()

        with patch("ignition_toolkit.api.routers.auth.get_rbac_manager", return_value=mock_rbac):
            result = asyncio.run(get_current_user_info(user=user))

        assert result["is_authenticated"] is True
        assert result["role"] == "admin"
        assert "permissions" in result
        assert Permission.PLAYBOOK_READ.value in result["permissions"]

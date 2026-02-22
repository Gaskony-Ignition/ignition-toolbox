"""
Tests for credentials API endpoints.

Tests list, create, update, and delete credential operations using a mocked
CredentialVault so no real filesystem or encryption work is performed.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from ignition_toolkit.credentials.models import Credential


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_credential(name="test-cred", username="admin", gateway_url=None, description=""):
    """Return a Credential dataclass instance with dummy values."""
    return Credential(
        name=name,
        username=username,
        password="<encrypted>",
        gateway_url=gateway_url,
        description=description,
    )


def _mock_vault(*, list_return=None, get_return=None, delete_return=True):
    """Return a MagicMock vault pre-configured with common return values."""
    vault = MagicMock()
    vault.list_credentials.return_value = list_return if list_return is not None else []
    vault.get_credential.return_value = get_return
    vault.save_credential.return_value = None
    vault.delete_credential.return_value = delete_return
    return vault


# ---------------------------------------------------------------------------
# list_credentials
# ---------------------------------------------------------------------------


class TestListCredentials:
    """Tests for GET /api/credentials"""

    def test_returns_empty_list_when_vault_is_empty(self):
        """When the vault has no entries, the response must be an empty list."""
        from ignition_toolkit.api.routers.credentials import list_credentials

        vault = _mock_vault(list_return=[])
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            result = asyncio.run(list_credentials())

        assert result == []

    def test_returns_list_with_credential_info_objects(self):
        """Credentials from the vault must be mapped to CredentialInfo objects."""
        from ignition_toolkit.api.routers.credentials import list_credentials, CredentialInfo

        stored = [
            _make_credential("cred-a", "alice", gateway_url="http://gw1:8088"),
            _make_credential("cred-b", "bob"),
        ]
        vault = _mock_vault(list_return=stored)
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            result = asyncio.run(list_credentials())

        assert len(result) == 2
        assert all(isinstance(r, CredentialInfo) for r in result)

    def test_returned_names_match_stored_credentials(self):
        """Credential names in the response must match those returned by the vault."""
        from ignition_toolkit.api.routers.credentials import list_credentials

        stored = [_make_credential("my-cred", "user1")]
        vault = _mock_vault(list_return=stored)
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            result = asyncio.run(list_credentials())

        assert result[0].name == "my-cred"
        assert result[0].username == "user1"

    def test_gateway_url_is_forwarded(self):
        """The gateway_url from the vault must appear in the response."""
        from ignition_toolkit.api.routers.credentials import list_credentials

        stored = [_make_credential("gw-cred", "admin", gateway_url="http://localhost:8088")]
        vault = _mock_vault(list_return=stored)
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            result = asyncio.run(list_credentials())

        assert result[0].gateway_url == "http://localhost:8088"

    def test_password_is_not_in_response(self):
        """The CredentialInfo model must not expose a 'password' field."""
        from ignition_toolkit.api.routers.credentials import list_credentials, CredentialInfo

        stored = [_make_credential("secret-cred", "root")]
        vault = _mock_vault(list_return=stored)
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            result = asyncio.run(list_credentials())

        assert hasattr(result[0], "name")
        assert not hasattr(result[0], "password"), "CredentialInfo must not expose 'password'"

    def test_vault_exception_raises_http_500(self):
        """When the vault raises an exception, list_credentials must respond with HTTP 500."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import list_credentials

        vault = MagicMock()
        vault.list_credentials.side_effect = RuntimeError("Vault corrupted")
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(list_credentials())

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# add_credential
# ---------------------------------------------------------------------------


class TestAddCredential:
    """Tests for POST /api/credentials"""

    def test_successful_create_returns_message_and_name(self):
        """Creating a new credential must return a dict with 'message' and 'name'."""
        from ignition_toolkit.api.routers.credentials import add_credential, CredentialCreate

        vault = _mock_vault(get_return=None)  # credential does not exist yet
        # get_credential raises ValueError when credential is not found (per vault logic)
        vault.get_credential.side_effect = ValueError("not found")

        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            payload = CredentialCreate(
                name="new-cred",
                username="newuser",
                password="secret",
                gateway_url="http://gw:8088",
            )
            result = asyncio.run(add_credential(payload))

        assert result["name"] == "new-cred"
        assert "message" in result

    def test_empty_name_raises_http_400(self):
        """A blank credential name must be rejected with HTTP 400."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import add_credential, CredentialCreate

        vault = _mock_vault()
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            payload = CredentialCreate(name="   ", username="u", password="p")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(add_credential(payload))

        assert exc_info.value.status_code == 400

    def test_duplicate_name_raises_http_400(self):
        """Adding a credential with an existing name must raise HTTP 400."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import add_credential, CredentialCreate

        existing = _make_credential("dup-cred")
        vault = _mock_vault(get_return=existing)

        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            payload = CredentialCreate(name="dup-cred", username="u", password="p")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(add_credential(payload))

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    def test_save_credential_is_called_on_success(self):
        """On a successful create, vault.save_credential must be called exactly once."""
        from ignition_toolkit.api.routers.credentials import add_credential, CredentialCreate

        vault = _mock_vault()
        vault.get_credential.side_effect = ValueError("not found")

        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            payload = CredentialCreate(name="stored-cred", username="u", password="p")
            asyncio.run(add_credential(payload))

        vault.save_credential.assert_called_once()


# ---------------------------------------------------------------------------
# update_credential
# ---------------------------------------------------------------------------


class TestUpdateCredential:
    """Tests for PUT /api/credentials/{name}"""

    def test_update_non_existent_credential_raises_http_404(self):
        """Updating a credential that does not exist must raise HTTP 404."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import update_credential, CredentialCreate

        vault = _mock_vault(get_return=None)
        vault.get_credential.side_effect = ValueError("not found")

        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            payload = CredentialCreate(name="ghost", username="u", password="p")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(update_credential("ghost", payload))

        assert exc_info.value.status_code == 404

    def test_update_existing_credential_returns_message(self):
        """Updating an existing credential must return a dict with 'message' and 'name'."""
        from ignition_toolkit.api.routers.credentials import update_credential, CredentialCreate

        existing = _make_credential("real-cred")
        vault = _mock_vault(get_return=existing)

        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            payload = CredentialCreate(name="real-cred", username="newuser", password="newpass")
            result = asyncio.run(update_credential("real-cred", payload))

        assert result["name"] == "real-cred"
        assert "message" in result

    def test_update_calls_delete_then_save(self):
        """update_credential must delete the old entry and save the new one."""
        from ignition_toolkit.api.routers.credentials import update_credential, CredentialCreate

        existing = _make_credential("upd-cred")
        vault = _mock_vault(get_return=existing)

        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            payload = CredentialCreate(name="upd-cred", username="u2", password="p2")
            asyncio.run(update_credential("upd-cred", payload))

        vault.delete_credential.assert_called_once_with("upd-cred")
        vault.save_credential.assert_called_once()

    def test_update_empty_name_raises_http_400(self):
        """A blank path parameter name must be rejected with HTTP 400."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import update_credential, CredentialCreate

        vault = _mock_vault()
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            payload = CredentialCreate(name="any", username="u", password="p")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(update_credential("   ", payload))

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# delete_credential
# ---------------------------------------------------------------------------


class TestDeleteCredential:
    """Tests for DELETE /api/credentials/{name}"""

    def test_delete_non_existent_credential_raises_http_404(self):
        """Deleting a credential that does not exist must raise HTTP 404."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import delete_credential

        vault = _mock_vault(delete_return=False)
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_credential("missing-cred"))

        assert exc_info.value.status_code == 404

    def test_delete_existing_credential_returns_message(self):
        """Deleting an existing credential must return a dict with 'message' and 'name'."""
        from ignition_toolkit.api.routers.credentials import delete_credential

        vault = _mock_vault(delete_return=True)
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            result = asyncio.run(delete_credential("my-cred"))

        assert result["name"] == "my-cred"
        assert "message" in result

    def test_delete_calls_vault_delete(self):
        """delete_credential must call vault.delete_credential with the correct name."""
        from ignition_toolkit.api.routers.credentials import delete_credential

        vault = _mock_vault(delete_return=True)
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            asyncio.run(delete_credential("the-cred"))

        vault.delete_credential.assert_called_once_with("the-cred")

    def test_delete_empty_name_raises_http_400(self):
        """A blank name parameter must be rejected with HTTP 400."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import delete_credential

        vault = _mock_vault()
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_credential("   "))

        assert exc_info.value.status_code == 400

    def test_vault_exception_during_delete_raises_http_500(self):
        """When the vault raises an unexpected exception, HTTP 500 must be returned."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import delete_credential

        vault = MagicMock()
        vault.delete_credential.side_effect = RuntimeError("Disk full")
        with patch("ignition_toolkit.api.routers.credentials.CredentialVault", return_value=vault):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_credential("any-cred"))

        assert exc_info.value.status_code == 500

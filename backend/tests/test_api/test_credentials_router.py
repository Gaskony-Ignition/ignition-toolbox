"""
Tests for credential management API endpoints.

Tests list, get (via add/delete), and delete operations.
Uses direct function import + patch pattern.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_vault():
    """Return a mock CredentialVault that holds no credentials."""
    vault = MagicMock()
    vault.list_credentials.return_value = []
    vault.get_credential.side_effect = ValueError("Credential not found")
    vault.delete_credential.return_value = False
    return vault


class TestListCredentials:
    def test_list_credentials_returns_empty_list(self, mock_vault):
        """GET /api/credentials returns an empty list when vault is empty."""
        from ignition_toolkit.api.routers.credentials import list_credentials

        with patch(
            "ignition_toolkit.api.routers.credentials.CredentialVault",
            return_value=mock_vault,
        ):
            result = asyncio.run(list_credentials())

        assert isinstance(result, list)
        assert result == []

    def test_list_credentials_returns_credentials_without_passwords(self, mock_vault):
        """GET /api/credentials returns credential info without exposing passwords."""
        from ignition_toolkit.credentials.models import Credential
        from ignition_toolkit.api.routers.credentials import list_credentials

        cred = Credential(
            name="prod-gateway",
            username="admin",
            password="secret123",
            gateway_url="http://localhost:8088",
            description="Production gateway",
        )
        mock_vault.list_credentials.return_value = [cred]

        with patch(
            "ignition_toolkit.api.routers.credentials.CredentialVault",
            return_value=mock_vault,
        ):
            result = asyncio.run(list_credentials())

        assert len(result) == 1
        entry = result[0]
        assert entry.name == "prod-gateway"
        assert entry.username == "admin"
        assert entry.gateway_url == "http://localhost:8088"
        # Passwords must not appear in the response model
        assert not hasattr(entry, "password")


class TestAddCredential:
    def test_add_credential_succeeds(self, mock_vault):
        """POST /api/credentials creates a new credential successfully."""
        from ignition_toolkit.api.routers.credentials import add_credential, CredentialCreate

        mock_vault.get_credential.side_effect = ValueError("not found")

        request = CredentialCreate(
            name="test-cred",
            username="user1",
            password="pass1",
            gateway_url="http://gw:8088",
            description="Test",
        )

        with patch(
            "ignition_toolkit.api.routers.credentials.CredentialVault",
            return_value=mock_vault,
        ):
            result = asyncio.run(add_credential(request))

        assert result["name"] == "test-cred"
        assert "message" in result

    def test_add_credential_rejects_empty_name(self, mock_vault):
        """POST /api/credentials raises 400 when name is blank."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import add_credential, CredentialCreate

        request = CredentialCreate(
            name="   ",
            username="user",
            password="pass",
        )

        with patch(
            "ignition_toolkit.api.routers.credentials.CredentialVault",
            return_value=mock_vault,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(add_credential(request))

        assert exc_info.value.status_code == 400

    def test_add_credential_rejects_duplicate(self, mock_vault):
        """POST /api/credentials raises 400 when credential already exists."""
        from fastapi import HTTPException
        from ignition_toolkit.credentials.models import Credential
        from ignition_toolkit.api.routers.credentials import add_credential, CredentialCreate

        existing = Credential(name="dup", username="u", password="p")
        mock_vault.get_credential.side_effect = None
        mock_vault.get_credential.return_value = existing

        request = CredentialCreate(name="dup", username="u", password="p")

        with patch(
            "ignition_toolkit.api.routers.credentials.CredentialVault",
            return_value=mock_vault,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(add_credential(request))

        assert exc_info.value.status_code == 400


class TestDeleteCredential:
    def test_delete_credential_raises_404_for_unknown_name(self, mock_vault):
        """DELETE /api/credentials/{name} returns 404 for a credential that doesn't exist."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import delete_credential

        mock_vault.delete_credential.return_value = False

        with patch(
            "ignition_toolkit.api.routers.credentials.CredentialVault",
            return_value=mock_vault,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_credential("nonexistent-credential"))

        assert exc_info.value.status_code == 404

    def test_delete_credential_succeeds_when_exists(self, mock_vault):
        """DELETE /api/credentials/{name} returns success when credential is found."""
        from ignition_toolkit.api.routers.credentials import delete_credential

        mock_vault.delete_credential.return_value = True

        with patch(
            "ignition_toolkit.api.routers.credentials.CredentialVault",
            return_value=mock_vault,
        ):
            result = asyncio.run(delete_credential("existing-cred"))

        assert result["name"] == "existing-cred"
        assert "message" in result


class TestUpdateCredential:
    def test_update_credential_raises_404_when_not_found(self, mock_vault):
        """PUT /api/credentials/{name} returns 404 when credential doesn't exist."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import update_credential, CredentialCreate

        mock_vault.get_credential.side_effect = ValueError("not found")

        request = CredentialCreate(name="x", username="u", password="p")

        with patch(
            "ignition_toolkit.api.routers.credentials.CredentialVault",
            return_value=mock_vault,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(update_credential("nonexistent", request))

        assert exc_info.value.status_code == 404

    def test_update_credential_rejects_empty_name(self, mock_vault):
        """PUT /api/credentials/{name} returns 400 for blank path parameter name."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.credentials import update_credential, CredentialCreate

        request = CredentialCreate(name="valid", username="u", password="p")

        with patch(
            "ignition_toolkit.api.routers.credentials.CredentialVault",
            return_value=mock_vault,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(update_credential("   ", request))

        assert exc_info.value.status_code == 400

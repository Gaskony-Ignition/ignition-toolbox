"""
Tests for credential vault functionality

Tests encryption, storage, and retrieval of credentials.
"""

import sys

import pytest
from pathlib import Path
from datetime import datetime, UTC

from ignition_toolkit.credentials.vault import CredentialVault
from ignition_toolkit.credentials.models import Credential


class TestCredentialVaultBasic:
    """Test basic credential vault operations"""

    def test_create_vault_creates_directory(self, tmp_path):
        """Test that vault creates directory if it doesn't exist"""
        vault_path = tmp_path / "test_vault"
        vault = CredentialVault(vault_path=vault_path)

        assert vault_path.exists()
        assert vault.credentials_file.exists()

    def test_save_and_retrieve_credential(self, tmp_path):
        """Test saving and retrieving a credential"""
        vault = CredentialVault(vault_path=tmp_path)

        credential = Credential(
            name="test-gateway",
            username="admin",
            password="secret123",
            gateway_url="http://localhost:8088",
            description="Test gateway credentials",
        )

        vault.save_credential(credential)

        # Retrieve and verify
        retrieved = vault.get_credential("test-gateway")

        assert retrieved is not None
        assert retrieved.name == "test-gateway"
        assert retrieved.username == "admin"
        assert retrieved.password == "secret123"
        assert retrieved.gateway_url == "http://localhost:8088"
        assert retrieved.description == "Test gateway credentials"

    def test_get_nonexistent_credential_returns_none(self, tmp_path):
        """Test that getting a nonexistent credential returns None"""
        vault = CredentialVault(vault_path=tmp_path)

        result = vault.get_credential("nonexistent")

        assert result is None

    def test_list_credentials(self, tmp_path):
        """Test listing all credentials"""
        vault = CredentialVault(vault_path=tmp_path)

        # Add multiple credentials
        for i in range(3):
            credential = Credential(
                name=f"gateway-{i}",
                username="admin",
                password=f"pass{i}",
                gateway_url=f"http://gateway{i}:8088",
            )
            vault.save_credential(credential)

        # List all
        credentials = vault.list_credentials()

        assert len(credentials) == 3
        names = [c.name for c in credentials]
        assert "gateway-0" in names
        assert "gateway-1" in names
        assert "gateway-2" in names

    def test_delete_credential(self, tmp_path):
        """Test deleting a credential"""
        vault = CredentialVault(vault_path=tmp_path)

        credential = Credential(
            name="to-delete",
            username="admin",
            password="secret",
        )
        vault.save_credential(credential)

        # Verify it exists
        assert vault.get_credential("to-delete") is not None

        # Delete it
        result = vault.delete_credential("to-delete")

        assert result is True
        assert vault.get_credential("to-delete") is None

    def test_delete_nonexistent_credential_returns_false(self, tmp_path):
        """Test that deleting nonexistent credential returns False"""
        vault = CredentialVault(vault_path=tmp_path)

        result = vault.delete_credential("nonexistent")

        assert result is False

    def test_update_existing_credential(self, tmp_path):
        """Test updating an existing credential"""
        vault = CredentialVault(vault_path=tmp_path)

        # Create initial credential
        credential1 = Credential(
            name="my-gateway",
            username="admin",
            password="old-password",
        )
        vault.save_credential(credential1)

        # Update with new values
        credential2 = Credential(
            name="my-gateway",
            username="admin",
            password="new-password",
            description="Updated description",
        )
        vault.save_credential(credential2)

        # Verify update
        retrieved = vault.get_credential("my-gateway")

        assert retrieved.password == "new-password"
        assert retrieved.description == "Updated description"

        # Only one credential should exist
        all_creds = vault.list_credentials()
        assert len(all_creds) == 1


class TestCredentialVaultEncryption:
    """Test credential encryption functionality"""

    def test_password_is_encrypted_in_storage(self, tmp_path):
        """Test that passwords are encrypted when stored"""
        vault = CredentialVault(vault_path=tmp_path)

        credential = Credential(
            name="encrypted-test",
            username="admin",
            password="my-secret-password",
        )
        vault.save_credential(credential)

        # Read raw file content
        raw_content = vault.credentials_file.read_text()

        # Password should NOT appear in plaintext
        assert "my-secret-password" not in raw_content

    def test_encryption_key_is_created(self, tmp_path):
        """Test that encryption key file is created"""
        vault = CredentialVault(vault_path=tmp_path)

        assert vault.encryption_key_path.exists()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix file permissions not available on Windows")
    def test_credentials_file_has_restricted_permissions(self, tmp_path):
        """Test that credentials file has restricted permissions"""
        vault = CredentialVault(vault_path=tmp_path)

        # Save something to create the file
        credential = Credential(
            name="test",
            username="admin",
            password="secret",
        )
        vault.save_credential(credential)

        # Check file permissions (should be 0o600 - owner read/write only)
        mode = vault.credentials_file.stat().st_mode & 0o777
        assert mode == 0o600

    def test_vault_persistence_across_instances(self, tmp_path):
        """Test that credentials persist across vault instances"""
        # First instance - save credential
        vault1 = CredentialVault(vault_path=tmp_path)
        credential = Credential(
            name="persistent",
            username="admin",
            password="secret",
        )
        vault1.save_credential(credential)

        # Second instance - should see the credential
        vault2 = CredentialVault(vault_path=tmp_path)
        retrieved = vault2.get_credential("persistent")

        assert retrieved is not None
        assert retrieved.password == "secret"


class TestCredentialVaultEdgeCases:
    """Test edge cases and error handling"""

    def test_special_characters_in_password(self, tmp_path):
        """Test credentials with special characters in password"""
        vault = CredentialVault(vault_path=tmp_path)

        special_password = r"p@$$w0rd!#$%^&*(){}[]|\\:\";<>?,./"

        credential = Credential(
            name="special-chars",
            username="admin",
            password=special_password,
        )
        vault.save_credential(credential)

        retrieved = vault.get_credential("special-chars")
        assert retrieved.password == special_password

    def test_unicode_in_credentials(self, tmp_path):
        """Test credentials with unicode characters"""
        vault = CredentialVault(vault_path=tmp_path)

        credential = Credential(
            name="unicode-test",
            username="администратор",  # Russian for "administrator"
            password="密码123",  # Chinese for "password"
            description="日本語の説明",  # Japanese description
        )
        vault.save_credential(credential)

        retrieved = vault.get_credential("unicode-test")
        assert retrieved.username == "администратор"
        assert retrieved.password == "密码123"
        assert retrieved.description == "日本語の説明"

    def test_empty_password(self, tmp_path):
        """Test credential with empty password"""
        vault = CredentialVault(vault_path=tmp_path)

        credential = Credential(
            name="empty-pass",
            username="admin",
            password="",
        )
        vault.save_credential(credential)

        retrieved = vault.get_credential("empty-pass")
        assert retrieved.password == ""

    def test_very_long_password(self, tmp_path):
        """Test credential with very long password"""
        vault = CredentialVault(vault_path=tmp_path)

        long_password = "x" * 10000  # 10KB password

        credential = Credential(
            name="long-pass",
            username="admin",
            password=long_password,
        )
        vault.save_credential(credential)

        retrieved = vault.get_credential("long-pass")
        assert retrieved.password == long_password
        assert len(retrieved.password) == 10000

    def test_credential_timestamps(self, tmp_path):
        """Test that credentials have timestamps"""
        vault = CredentialVault(vault_path=tmp_path)

        before = datetime.now(UTC)

        credential = Credential(
            name="timed",
            username="admin",
            password="secret",
        )
        vault.save_credential(credential)

        after = datetime.now(UTC)

        retrieved = vault.get_credential("timed")

        # created_at should be set
        assert retrieved.created_at is not None
        # Should be between before and after
        assert before <= retrieved.created_at <= after


class TestCredentialModel:
    """Test Credential model"""

    def test_credential_creation(self):
        """Test creating a credential"""
        credential = Credential(
            name="test",
            username="admin",
            password="secret",
            gateway_url="http://localhost:8088",
            description="Test credential",
        )

        assert credential.name == "test"
        assert credential.username == "admin"
        assert credential.password == "secret"
        assert credential.gateway_url == "http://localhost:8088"
        assert credential.description == "Test credential"

    def test_credential_defaults(self):
        """Test credential default values"""
        credential = Credential(
            name="minimal",
            username="admin",
            password="secret",
        )

        assert credential.gateway_url is None
        assert credential.description is None

    def test_credential_to_dict(self):
        """Test credential to_dict method"""
        credential = Credential(
            name="test",
            username="admin",
            password="secret",
            gateway_url="http://localhost:8088",
        )

        d = credential.to_dict()

        assert d["name"] == "test"
        assert d["username"] == "admin"
        assert d["password"] == "secret"
        assert d["gateway_url"] == "http://localhost:8088"

    def test_credential_from_dict(self):
        """Test credential from_dict method"""
        data = {
            "name": "test",
            "username": "admin",
            "password": "secret",
            "gateway_url": "http://localhost:8088",
        }

        credential = Credential.from_dict(data)

        assert credential.name == "test"
        assert credential.username == "admin"
        assert credential.password == "secret"

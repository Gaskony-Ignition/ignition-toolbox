"""
Credential vault for secure local storage
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from ignition_toolkit.config import get_toolkit_data_dir, migrate_credentials_if_needed
from ignition_toolkit.credentials.encryption import CredentialEncryption
from ignition_toolkit.credentials.models import Credential

logger = logging.getLogger(__name__)


class CredentialVault:
    """
    Secure credential storage with Fernet encryption

    Credentials are stored in data/.ignition-toolkit/credentials.json (encrypted)
    Encryption key is stored in data/.ignition-toolkit/encryption.key

    Location is determined by get_toolkit_data_dir() which provides a consistent
    path regardless of HOME environment variable changes.

    Both files are excluded from git via .gitignore
    """

    def __init__(self, vault_path: Path | None = None):
        """
        Initialize credential vault

        Args:
            vault_path: Path to vault directory. If None, uses get_toolkit_data_dir()
        """
        if vault_path is None:
            # Use consistent data directory instead of Path.home()
            vault_path = get_toolkit_data_dir()
            # Migrate old credentials if this is first time using new location
            migrate_credentials_if_needed()

        self.vault_path = vault_path
        self.credentials_file = vault_path / "credentials.json"
        self.encryption_key_path = vault_path / "encryption.key"
        self.encryption = CredentialEncryption(self.encryption_key_path)

        # Ensure vault directory exists
        self.vault_path.mkdir(parents=True, exist_ok=True)

        # Ensure credentials file exists
        if not self.credentials_file.exists():
            self._save_credentials_file({})

    def _save_credentials_file(self, data: dict) -> None:
        """Save credentials to encrypted file"""
        # Encrypt the entire JSON structure
        json_str = json.dumps(data, indent=2)
        encrypted = self.encryption.encrypt(json_str)

        self.credentials_file.write_text(encrypted)
        self.credentials_file.chmod(0o600)  # Owner read/write only

        logger.debug(f"Credentials saved to {self.credentials_file}")

    def _load_credentials_file(self) -> dict:
        """Load credentials from encrypted file"""
        if not self.credentials_file.exists():
            return {}

        encrypted = self.credentials_file.read_text()

        try:
            json_str = self.encryption.decrypt(encrypted)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise ValueError("Failed to decrypt credentials. Key may be corrupted.") from e

    def save_credential(self, credential: Credential) -> None:
        """
        Save or update a credential

        Args:
            credential: Credential to save
        """
        credentials_data = self._load_credentials_file()

        # Encrypt the password before storing
        encrypted_password = self.encryption.encrypt(credential.password)

        # Store credential data
        credentials_data[credential.name] = {
            "name": credential.name,
            "username": credential.username,
            "password": encrypted_password,  # Already encrypted
            "gateway_url": credential.gateway_url,
            "description": credential.description,
            "created_at": (
                credential.created_at.isoformat()
                if credential.created_at
                else datetime.now(UTC).isoformat()
            ),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        self._save_credentials_file(credentials_data)
        logger.info(f"Credential '{credential.name}' saved successfully")

    def get_credential(self, name: str) -> Credential | None:
        """
        Retrieve a credential by name

        Args:
            name: Credential name

        Returns:
            Credential object with decrypted password, or None if not found
        """
        credentials_data = self._load_credentials_file()

        if name not in credentials_data:
            logger.warning(f"Credential '{name}' not found")
            return None

        cred_data = credentials_data[name]

        # Decrypt password
        decrypted_password = self.encryption.decrypt(cred_data["password"])

        # Create credential object
        return Credential(
            name=cred_data["name"],
            username=cred_data["username"],
            password=decrypted_password,
            gateway_url=cred_data.get("gateway_url"),
            description=cred_data.get("description"),
            created_at=(
                datetime.fromisoformat(cred_data["created_at"])
                if cred_data.get("created_at")
                else None
            ),
            updated_at=(
                datetime.fromisoformat(cred_data["updated_at"])
                if cred_data.get("updated_at")
                else None
            ),
        )

    def list_credentials(self) -> list[Credential]:
        """
        List all stored credentials (without passwords)

        Returns:
            List of Credential objects with empty passwords
        """
        credentials_data = self._load_credentials_file()

        credentials = []
        for name, cred_data in credentials_data.items():
            credentials.append(
                Credential(
                    name=cred_data["name"],
                    username=cred_data["username"],
                    password="<encrypted>",  # Don't return actual password
                    gateway_url=cred_data.get("gateway_url"),
                    description=cred_data.get("description"),
                    created_at=(
                        datetime.fromisoformat(cred_data["created_at"])
                        if cred_data.get("created_at")
                        else None
                    ),
                    updated_at=(
                        datetime.fromisoformat(cred_data["updated_at"])
                        if cred_data.get("updated_at")
                        else None
                    ),
                )
            )

        return sorted(credentials, key=lambda c: c.name)

    def delete_credential(self, name: str) -> bool:
        """
        Delete a credential

        Args:
            name: Credential name

        Returns:
            True if deleted, False if not found
        """
        credentials_data = self._load_credentials_file()

        if name not in credentials_data:
            logger.warning(f"Credential '{name}' not found for deletion")
            return False

        del credentials_data[name]
        self._save_credentials_file(credentials_data)

        logger.info(f"Credential '{name}' deleted")
        return True

    def credential_exists(self, name: str) -> bool:
        """
        Check if a credential exists

        Args:
            name: Credential name

        Returns:
            True if exists, False otherwise
        """
        credentials_data = self._load_credentials_file()
        return name in credentials_data

    def initialize(self) -> None:
        """
        Initialize credential vault

        Creates vault directory and files if they don't exist.
        Safe to call multiple times (idempotent).
        """
        # Ensure vault directory exists
        self.vault_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Vault directory ready: {self.vault_path}")

        # Ensure encryption key exists
        if not self.encryption_key_path.exists():
            # This will create a new key
            _ = self.encryption.key
            logger.info(f"Created new encryption key: {self.encryption_key_path}")
        else:
            logger.debug(f"Encryption key exists: {self.encryption_key_path}")

        # Ensure credentials file exists
        if not self.credentials_file.exists():
            self._save_credentials_file({})
            logger.info(f"Created new credentials file: {self.credentials_file}")
        else:
            logger.debug(f"Credentials file exists: {self.credentials_file}")

        logger.info("Credential vault initialized")

    def test_encryption(self) -> bool:
        """
        Test encryption/decryption functionality

        Returns:
            True if encryption works correctly, False otherwise
        """
        test_string = "test_encryption_12345"

        try:
            # Test encrypt/decrypt
            encrypted = self.encryption.encrypt(test_string)
            decrypted = self.encryption.decrypt(encrypted)

            if decrypted != test_string:
                logger.error("Encryption test failed: decrypted value doesn't match original")
                return False

            logger.debug("Encryption test passed")
            return True

        except Exception as e:
            logger.error(f"Encryption test failed: {e}")
            return False


# Global vault instance (singleton)
_credential_vault: CredentialVault | None = None


def get_credential_vault(vault_path: Path | None = None) -> CredentialVault:
    """
    Get the global credential vault instance (singleton pattern)

    Args:
        vault_path: Path to vault directory (only used on first call)

    Returns:
        CredentialVault instance
    """
    global _credential_vault
    if _credential_vault is None:
        _credential_vault = CredentialVault(vault_path)
    return _credential_vault

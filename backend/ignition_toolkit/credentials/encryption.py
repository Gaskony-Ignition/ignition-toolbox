"""
Credential encryption using Fernet (symmetric encryption)
"""

import logging
from pathlib import Path

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """
    Handles encryption/decryption of credentials using Fernet

    The encryption key is stored locally and never committed to git.
    Loss of the key means loss of all stored credentials.
    """

    def __init__(self, key_path: Path | None = None):
        """
        Initialize encryption handler

        Args:
            key_path: Path to encryption key file. If None, uses consistent data directory.
        """
        if key_path is None:
            from ignition_toolkit.config import get_toolkit_data_dir

            key_path = get_toolkit_data_dir() / "encryption.key"

        self.key_path = key_path
        self._fernet: Fernet | None = None

    def _ensure_key_exists(self) -> None:
        """Create encryption key if it doesn't exist"""
        if not self.key_path.exists():
            logger.info(f"Generating new encryption key: {self.key_path}")

            # Create directory
            self.key_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate and save key
            key = Fernet.generate_key()
            self.key_path.write_bytes(key)

            # Restrict permissions (owner read/write only)
            self.key_path.chmod(0o600)

            logger.info("Encryption key generated successfully")

    def _load_key(self) -> bytes:
        """Load encryption key from file"""
        self._ensure_key_exists()
        return self.key_path.read_bytes()

    @property
    def fernet(self) -> Fernet:
        """Get Fernet cipher instance (lazy-loaded)"""
        if self._fernet is None:
            key = self._load_key()
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt encrypted string

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        decrypted_bytes = self.fernet.decrypt(encrypted.encode())
        return decrypted_bytes.decode()

    def rotate_key(self, new_key_path: Path) -> None:
        """
        Rotate encryption key (for advanced users)

        WARNING: This requires re-encrypting all stored credentials

        Args:
            new_key_path: Path to new encryption key
        """
        # This would require:
        # 1. Decrypt all credentials with old key
        # 2. Encrypt all credentials with new key
        # 3. Replace key file
        # Not implementing in v1.0 - future feature
        raise NotImplementedError("Key rotation not yet implemented")

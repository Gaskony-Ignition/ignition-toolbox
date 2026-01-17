"""
API Key service for API Explorer

Handles secure storage and retrieval of Ignition Gateway API keys.
Uses the same Fernet encryption as credentials vault.
"""

import logging
from datetime import UTC, datetime

from ignition_toolkit.credentials.encryption import CredentialEncryption
from ignition_toolkit.storage.database import get_database
from ignition_toolkit.storage.models import APIKeyModel

logger = logging.getLogger(__name__)


class APIKeyService:
    """
    Service for managing Ignition Gateway API keys

    Uses Fernet encryption for secure storage.
    """

    def __init__(self):
        self.encryption = CredentialEncryption()
        self.db = get_database()

    def list_api_keys(self) -> list[dict]:
        """
        List all API keys (without exposing encrypted values)

        Returns:
            List of API key info dictionaries
        """
        with self.db.session_scope() as session:
            keys = session.query(APIKeyModel).order_by(APIKeyModel.name).all()
            return [key.to_dict() for key in keys]

    def get_api_key(self, name: str) -> APIKeyModel | None:
        """
        Get an API key by name

        Args:
            name: API key name

        Returns:
            APIKeyModel or None if not found
        """
        with self.db.session_scope() as session:
            return session.query(APIKeyModel).filter(APIKeyModel.name == name).first()

    def get_decrypted_key(self, name: str) -> str | None:
        """
        Get the decrypted API key value

        Args:
            name: API key name

        Returns:
            Decrypted API key string or None
        """
        with self.db.session_scope() as session:
            key = session.query(APIKeyModel).filter(APIKeyModel.name == name).first()
            if not key:
                return None
            return self.encryption.decrypt(key.api_key_encrypted)

    def create_api_key(
        self,
        name: str,
        gateway_url: str,
        api_key: str,
        description: str | None = None,
    ) -> dict:
        """
        Create a new API key entry

        Args:
            name: Unique name for this API key
            gateway_url: Ignition Gateway URL
            api_key: The actual API key to store (will be encrypted)
            description: Optional description

        Returns:
            Created API key info dict

        Raises:
            ValueError: If name already exists
        """
        with self.db.session_scope() as session:
            # Check if name already exists
            existing = session.query(APIKeyModel).filter(APIKeyModel.name == name).first()
            if existing:
                raise ValueError(f"API key with name '{name}' already exists")

            # Encrypt the API key
            encrypted_key = self.encryption.encrypt(api_key)

            # Create new entry
            key_model = APIKeyModel(
                name=name,
                gateway_url=gateway_url,
                api_key_encrypted=encrypted_key,
                description=description,
            )
            session.add(key_model)
            session.flush()

            logger.info(f"Created API key: {name}")
            return key_model.to_dict()

    def update_api_key(
        self,
        name: str,
        gateway_url: str | None = None,
        api_key: str | None = None,
        description: str | None = None,
    ) -> dict:
        """
        Update an existing API key

        Args:
            name: API key name to update
            gateway_url: New gateway URL (optional)
            api_key: New API key value (optional)
            description: New description (optional)

        Returns:
            Updated API key info dict

        Raises:
            ValueError: If API key not found
        """
        with self.db.session_scope() as session:
            key = session.query(APIKeyModel).filter(APIKeyModel.name == name).first()
            if not key:
                raise ValueError(f"API key '{name}' not found")

            if gateway_url is not None:
                key.gateway_url = gateway_url
            if api_key is not None:
                key.api_key_encrypted = self.encryption.encrypt(api_key)
            if description is not None:
                key.description = description

            session.flush()
            logger.info(f"Updated API key: {name}")
            return key.to_dict()

    def delete_api_key(self, name: str) -> bool:
        """
        Delete an API key

        Args:
            name: API key name to delete

        Returns:
            True if deleted, False if not found
        """
        with self.db.session_scope() as session:
            key = session.query(APIKeyModel).filter(APIKeyModel.name == name).first()
            if not key:
                return False

            session.delete(key)
            logger.info(f"Deleted API key: {name}")
            return True

    def update_last_used(self, name: str) -> None:
        """
        Update the last_used timestamp for an API key

        Args:
            name: API key name
        """
        with self.db.session_scope() as session:
            key = session.query(APIKeyModel).filter(APIKeyModel.name == name).first()
            if key:
                key.last_used = datetime.now(UTC)

    def get_key_for_gateway(self, gateway_url: str) -> tuple[str, str] | None:
        """
        Get the first API key for a given gateway URL

        Args:
            gateway_url: Gateway URL to look up

        Returns:
            Tuple of (key_name, decrypted_api_key) or None
        """
        with self.db.session_scope() as session:
            key = (
                session.query(APIKeyModel)
                .filter(APIKeyModel.gateway_url == gateway_url)
                .first()
            )
            if not key:
                return None
            return (key.name, self.encryption.decrypt(key.api_key_encrypted))

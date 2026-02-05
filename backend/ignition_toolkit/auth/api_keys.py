"""
API Key Management

Handles creation, validation, and management of API keys for authentication.
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    """Represents an API key"""
    id: str
    name: str
    key_hash: str  # SHA-256 hash of the key
    user_id: str | None = None
    role: str = "user"  # admin, user, readonly
    scopes: list[str] = field(default_factory=list)  # Specific permissions
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    last_used: datetime | None = None
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_hash: bool = False) -> dict:
        """Convert to dictionary"""
        result = {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "role": self.role,
            "scopes": self.scopes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }
        if include_hash:
            result["key_hash"] = self.key_hash
        return result

    def is_expired(self) -> bool:
        """Check if key is expired"""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)"""
        return self.is_active and not self.is_expired()


class APIKeyManager:
    """
    Manages API keys for authentication

    Features:
    - Generate secure API keys
    - Validate keys against stored hashes
    - Support for key expiration
    - Role and scope management

    Example:
        manager = APIKeyManager()

        # Create a new API key
        key, api_key = manager.create_key(
            name="My API Key",
            role="user",
            expires_in_days=30
        )
        # key is the actual key to give to user (only shown once)
        # api_key is the APIKey object

        # Validate a key
        api_key = manager.validate_key(key)
        if api_key:
            print(f"Valid key for role: {api_key.role}")
    """

    def __init__(self):
        """Initialize API key manager"""
        self._keys: dict[str, APIKey] = {}  # id -> APIKey
        self._key_hashes: dict[str, str] = {}  # hash -> id
        logger.info("APIKeyManager initialized")

    def create_key(
        self,
        name: str,
        user_id: str | None = None,
        role: str = "user",
        scopes: list[str] | None = None,
        expires_in_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, APIKey]:
        """
        Create a new API key

        Args:
            name: Human-readable name for the key
            user_id: Optional user ID to associate
            role: Role for RBAC (admin, user, readonly)
            scopes: Specific permissions
            expires_in_days: Days until expiration (None = never)
            metadata: Additional metadata

        Returns:
            Tuple of (raw_key, APIKey object)
            The raw_key is only returned once and should be given to the user
        """
        # Generate secure random key
        raw_key = f"itk_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)
        key_id = secrets.token_hex(16)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        api_key = APIKey(
            id=key_id,
            name=name,
            key_hash=key_hash,
            user_id=user_id,
            role=role,
            scopes=scopes or [],
            expires_at=expires_at,
            metadata=metadata or {},
        )

        self._keys[key_id] = api_key
        self._key_hashes[key_hash] = key_id

        logger.info(f"Created API key '{name}' with role '{role}'")

        return raw_key, api_key

    def validate_key(self, raw_key: str) -> APIKey | None:
        """
        Validate an API key

        Args:
            raw_key: The raw API key string

        Returns:
            APIKey object if valid, None otherwise
        """
        if not raw_key or not raw_key.startswith("itk_"):
            return None

        key_hash = self._hash_key(raw_key)
        key_id = self._key_hashes.get(key_hash)

        if not key_id:
            return None

        api_key = self._keys.get(key_id)
        if not api_key:
            return None

        if not api_key.is_valid():
            return None

        # Update last used
        api_key.last_used = datetime.now(UTC)

        return api_key

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key

        Args:
            key_id: ID of the key to revoke

        Returns:
            True if revoked, False if not found
        """
        api_key = self._keys.get(key_id)
        if not api_key:
            return False

        api_key.is_active = False
        logger.info(f"Revoked API key '{api_key.name}'")
        return True

    def delete_key(self, key_id: str) -> bool:
        """
        Delete an API key

        Args:
            key_id: ID of the key to delete

        Returns:
            True if deleted, False if not found
        """
        api_key = self._keys.get(key_id)
        if not api_key:
            return False

        del self._key_hashes[api_key.key_hash]
        del self._keys[key_id]
        logger.info(f"Deleted API key '{api_key.name}'")
        return True

    def get_key(self, key_id: str) -> APIKey | None:
        """Get API key by ID"""
        return self._keys.get(key_id)

    def list_keys(self, user_id: str | None = None) -> list[APIKey]:
        """
        List all API keys

        Args:
            user_id: Filter by user ID (None = all)

        Returns:
            List of APIKey objects
        """
        keys = list(self._keys.values())
        if user_id:
            keys = [k for k in keys if k.user_id == user_id]
        return keys

    def update_key(
        self,
        key_id: str,
        name: str | None = None,
        role: str | None = None,
        scopes: list[str] | None = None,
        is_active: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> APIKey | None:
        """
        Update an API key

        Args:
            key_id: ID of key to update
            name: New name (optional)
            role: New role (optional)
            scopes: New scopes (optional)
            is_active: New active status (optional)
            metadata: Metadata to merge (optional)

        Returns:
            Updated APIKey or None if not found
        """
        api_key = self._keys.get(key_id)
        if not api_key:
            return None

        if name is not None:
            api_key.name = name
        if role is not None:
            api_key.role = role
        if scopes is not None:
            api_key.scopes = scopes
        if is_active is not None:
            api_key.is_active = is_active
        if metadata is not None:
            api_key.metadata.update(metadata)

        logger.info(f"Updated API key '{api_key.name}'")
        return api_key

    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(raw_key.encode()).hexdigest()


# Global instance
_api_key_manager: APIKeyManager | None = None


def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager

"""
Credential data models
"""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class Credential:
    """
    Represents a stored credential

    Attributes:
        name: Unique identifier for the credential
        username: Username or account name
        password: Password (encrypted at rest)
        gateway_url: Optional Gateway URL for convenience
        description: Optional description
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    name: str
    username: str
    password: str
    gateway_url: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Set timestamps if not provided"""
        now = datetime.now(UTC)
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "username": self.username,
            "password": self.password,
            "gateway_url": self.gateway_url,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Credential":
        """Create from dictionary"""
        created_at = None
        updated_at = None

        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            name=data["name"],
            username=data["username"],
            password=data["password"],
            gateway_url=data.get("gateway_url"),
            description=data.get("description"),
            created_at=created_at,
            updated_at=updated_at,
        )

"""
Core interfaces and protocols

Defines abstract base classes and protocols for dependency injection
and loose coupling between modules.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, ContextManager, Protocol

from sqlalchemy.orm import Session


class IDatabase(Protocol):
    """Protocol for database implementations"""

    @property
    def database_path(self) -> Path:
        """Database file path"""
        ...

    def create_tables(self) -> None:
        """Create all database tables"""
        ...

    @contextmanager
    def session_scope(self) -> ContextManager[Session]:
        """Provide a transactional scope for database operations"""
        ...

    def verify_schema(self) -> bool:
        """
        Verify database schema is valid

        Returns:
            bool: True if schema is valid
        """
        ...


class ICredentialVault(Protocol):
    """Protocol for credential vault implementations"""

    @property
    def vault_path(self) -> Path:
        """Vault file path"""
        ...

    def save_credential(self, credential: Any) -> None:
        """Save a credential to the vault"""
        ...

    def get_credential(self, name: str) -> Any:
        """Get a credential by name"""
        ...

    def list_credentials(self) -> list[str]:
        """List all credential names"""
        ...

    def delete_credential(self, name: str) -> None:
        """Delete a credential"""
        ...

    def initialize(self) -> None:
        """Initialize vault (create file if needed)"""
        ...

    def test_encryption(self) -> bool:
        """Test vault encryption/decryption"""
        ...


class IGatewayClient(Protocol):
    """Protocol for Gateway client implementations"""

    async def __aenter__(self) -> "IGatewayClient":
        """Async context manager entry"""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        ...

    async def login(self, username: str, password: str) -> None:
        """Login to Gateway"""
        ...

    async def logout(self) -> None:
        """Logout from Gateway"""
        ...


class IBrowserManager(Protocol):
    """Protocol for browser manager implementations"""

    async def start(self) -> None:
        """Start browser instance"""
        ...

    async def stop(self) -> None:
        """Stop browser instance"""
        ...

    async def navigate(self, url: str) -> None:
        """Navigate to URL"""
        ...


class IPlaybookEngine(Protocol):
    """Protocol for playbook engine implementations"""

    async def execute_playbook(
        self,
        playbook: Any,
        parameters: dict[str, Any],
        base_path: Path | None = None,
        execution_id: str | None = None,
    ) -> Any:
        """Execute a playbook"""
        ...

    async def pause(self) -> None:
        """Pause execution"""
        ...

    async def resume(self) -> None:
        """Resume execution"""
        ...

    async def cancel(self) -> None:
        """Cancel execution"""
        ...


class IExecutionRepository(Protocol):
    """Protocol for execution repository implementations"""

    async def get_by_id(self, execution_id: str) -> Any | None:
        """Get execution by ID"""
        ...

    async def create(self, execution: Any) -> Any:
        """Create new execution"""
        ...

    async def update(self, execution: Any) -> Any:
        """Update execution"""
        ...

    async def list_recent(self, limit: int = 20) -> list[Any]:
        """List recent executions"""
        ...

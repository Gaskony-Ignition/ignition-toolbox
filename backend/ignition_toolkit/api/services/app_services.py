"""
Application Services Container

Centralized container for all application-level services.
Replaces module-level globals with proper dependency injection.
"""

import logging
from dataclasses import dataclass

from ignition_toolkit.api.services.execution_service import ExecutionService
from ignition_toolkit.api.services.websocket_manager import WebSocketManager
from ignition_toolkit.credentials import CredentialVault
from ignition_toolkit.playbook.execution_manager import ExecutionManager
from ignition_toolkit.playbook.metadata import PlaybookMetadataStore
from ignition_toolkit.storage import get_database, Database

logger = logging.getLogger(__name__)


@dataclass
class AppServices:
    """
    Container for all application-level services

    Provides centralized access to:
    - ExecutionManager (execution lifecycle)
    - WebSocketManager (WebSocket connections)
    - PlaybookMetadataStore (playbook metadata)
    - CredentialVault (credential encryption)
    - Database (SQLite persistence)
    """

    execution_manager: ExecutionManager
    execution_service: ExecutionService
    websocket_manager: WebSocketManager
    metadata_store: PlaybookMetadataStore
    credential_vault: CredentialVault
    database: Database

    @classmethod
    def create(cls, ttl_minutes: int = 30) -> "AppServices":
        """
        Create new AppServices instance with all dependencies

        Args:
            ttl_minutes: TTL for completed executions (default: 30)

        Returns:
            Initialized AppServices instance
        """
        logger.info("Initializing application services...")

        execution_manager = ExecutionManager(ttl_minutes=ttl_minutes)
        websocket_manager = WebSocketManager()
        metadata_store = PlaybookMetadataStore()
        credential_vault = CredentialVault()
        database = get_database()

        # Create execution service with WebSocket callbacks
        execution_service = ExecutionService(
            execution_manager=execution_manager,
            credential_vault=credential_vault,
            database=database,
            screenshot_callback=websocket_manager.broadcast_screenshot,
            state_update_callback=websocket_manager.broadcast_execution_state,
        )

        logger.info("✅ Application services initialized")

        return cls(
            execution_manager=execution_manager,
            execution_service=execution_service,
            websocket_manager=websocket_manager,
            metadata_store=metadata_store,
            credential_vault=credential_vault,
            database=database,
        )

    async def cleanup(self) -> None:
        """
        Cleanup all services (called on shutdown)
        """
        logger.info("Cleaning up application services...")

        # Cleanup execution manager
        await self.execution_manager.cleanup()

        # Close all WebSocket connections
        await self.websocket_manager.close_all()

        logger.info("✅ Application services cleaned up")

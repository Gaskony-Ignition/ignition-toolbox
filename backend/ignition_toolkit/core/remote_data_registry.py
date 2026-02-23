"""
Remote Data Registry - Singleton tracking all RemoteDataManager instances.

Provides a central point for checking updates across all registered
data components and querying their status.
"""

from __future__ import annotations

import logging
from typing import Any

from ignition_toolkit.core.remote_data import RemoteDataManager

logger = logging.getLogger(__name__)


class RemoteDataRegistry:
    """
    Singleton registry of all RemoteDataManager instances.

    Each component registers itself on initialization. The registry
    enables batch operations (check all for updates, get all status).
    """

    _managers: dict[str, RemoteDataManager] = {}

    @classmethod
    def register(cls, manager: RemoteDataManager) -> None:
        """Register a RemoteDataManager instance."""
        name = manager.config.component_name
        cls._managers[name] = manager
        logger.debug("Registered remote data component: %s", name)

    @classmethod
    def unregister(cls, component_name: str) -> None:
        """Unregister a component (mainly for testing)."""
        cls._managers.pop(component_name, None)

    @classmethod
    def get(cls, component_name: str) -> RemoteDataManager | None:
        """Get a specific manager by component name."""
        return cls._managers.get(component_name)

    @classmethod
    def get_all(cls) -> dict[str, RemoteDataManager]:
        """Get all registered managers."""
        return dict(cls._managers)

    @classmethod
    async def check_all_updates(
        cls,
        manifest_components: dict[str, dict] | None = None,
        force: bool = False,
    ) -> dict[str, dict[str, Any] | None]:
        """
        Check all registered components for updates.

        Args:
            manifest_components: Pre-fetched manifest component info (keyed by component_name).
            force: Force check even if cache is still fresh.

        Returns:
            Dict mapping component_name to update info (or None if no update).
        """
        results: dict[str, dict[str, Any] | None] = {}

        for name, manager in cls._managers.items():
            manifest_info = manifest_components.get(name) if manifest_components else None
            results[name] = await manager.check_for_update(
                manifest_info=manifest_info,
                force=force,
            )

        return results

    @classmethod
    def get_all_status(cls) -> dict[str, dict[str, Any]]:
        """Get status/metadata for all registered components."""
        return {
            name: manager.get_metadata()
            for name, manager in cls._managers.items()
        }

    @classmethod
    def reset(cls) -> None:
        """Clear all registered managers (for testing)."""
        cls._managers.clear()

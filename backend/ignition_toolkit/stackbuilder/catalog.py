"""
Service Catalog for Stack Builder

Loads and manages the catalog of available services for Docker Compose stacks.
Supports remote updates via RemoteDataManager.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

from ignition_toolkit.core.remote_data import RemoteDataConfig, RemoteDataManager
from ignition_toolkit.core.remote_data_registry import RemoteDataRegistry

logger = logging.getLogger(__name__)


def _get_data_path(filename: str) -> Path:
    """Get path to a stackbuilder data file, handling frozen mode."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "stackbuilder" / "data" / filename
    return Path(__file__).parent / "data" / filename


class ServiceCatalog:
    """
    Service catalog manager

    Loads the catalog.json file containing all available services
    and their default configurations.

    When no catalog_path is provided, uses RemoteDataManager for
    automatic remote update support. When catalog_path is explicitly
    provided (e.g. in tests), reads directly from that path.
    """

    def __init__(self, catalog_path: Path | None = None):
        """
        Initialize the service catalog

        Args:
            catalog_path: Path to catalog.json. If provided, uses direct file
                mode (for testing). If None, uses RemoteDataManager mode.
        """
        if catalog_path is not None:
            # Direct path mode (testing)
            self.catalog_path = catalog_path
            self._manager: RemoteDataManager | None = None
        else:
            # RemoteDataManager mode (production)
            self.catalog_path = None
            config = RemoteDataConfig(
                component_name="stackbuilder_catalog",
                filename="catalog.json",
                github_path="data/stackbuilder/catalog.json",
                bundled_path_fn=lambda: _get_data_path("catalog.json"),
                on_update=lambda: setattr(self, "_catalog", None),
            )
            self._manager = RemoteDataManager(config)
            RemoteDataRegistry.register(self._manager)

        self._catalog: dict[str, Any] | None = None

    def _load_catalog(self) -> dict[str, Any]:
        """Load the catalog from JSON file or RemoteDataManager"""
        if self._manager:
            # RemoteDataManager mode: load from user data dir or bundled
            try:
                data = self._manager.load()
                if isinstance(data, dict):
                    return data
                return {"applications": [], "categories": []}
            except Exception as e:
                logger.error("Failed to load catalog via RemoteDataManager: %s", e)
                return {"applications": [], "categories": []}

        # Direct file mode (testing)
        try:
            with open(self.catalog_path, encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Catalog file not found: {self.catalog_path}")
            return {"applications": [], "categories": []}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing catalog file: {e}")
            return {"applications": [], "categories": []}

    @property
    def catalog(self) -> dict[str, Any]:
        """Get the full catalog (lazy-loaded)"""
        if self._catalog is None:
            self._catalog = self._load_catalog()
        return self._catalog

    def get_applications(self) -> list[dict[str, Any]]:
        """Get all applications in the catalog"""
        return self.catalog.get("applications", [])

    def get_enabled_applications(self) -> list[dict[str, Any]]:
        """Get only enabled applications"""
        return [app for app in self.get_applications() if app.get("enabled", False)]

    def get_categories(self) -> list[dict[str, Any]]:
        """Get all categories"""
        return self.catalog.get("categories", [])

    def get_application_by_id(self, app_id: str) -> dict[str, Any] | None:
        """
        Get a specific application by ID

        Args:
            app_id: Application ID (e.g., "ignition", "postgres")

        Returns:
            Application dict or None if not found
        """
        for app in self.get_applications():
            if app.get("id") == app_id:
                return app
        return None

    def get_applications_by_category(self, category: str) -> list[dict[str, Any]]:
        """
        Get all applications in a category

        Args:
            category: Category name (e.g., "Databases", "SCADA")

        Returns:
            List of applications in the category
        """
        return [
            app
            for app in self.get_applications()
            if app.get("category") == category and app.get("enabled", False)
        ]

    def search_applications(self, query: str) -> list[dict[str, Any]]:
        """
        Search applications by name or description

        Args:
            query: Search query

        Returns:
            List of matching applications
        """
        query_lower = query.lower()
        results = []

        for app in self.get_enabled_applications():
            name = app.get("name", "").lower()
            description = app.get("description", "").lower()
            tags = [t.lower() for t in app.get("tags", [])]

            if (
                query_lower in name
                or query_lower in description
                or any(query_lower in tag for tag in tags)
            ):
                results.append(app)

        return results

    def get_application_as_dict(self) -> dict[str, dict[str, Any]]:
        """
        Get applications as a dict keyed by ID

        Returns:
            Dict mapping app_id to application config
        """
        return {app["id"]: app for app in self.get_applications()}

    def validate_instance_config(
        self, app_id: str, config: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate an instance configuration against the app schema

        Args:
            app_id: Application ID
            config: Instance configuration to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        app = self.get_application_by_id(app_id)
        if not app:
            return False, [f"Unknown application: {app_id}"]

        if not app.get("enabled", False):
            return False, [f"Application {app_id} is not enabled"]

        errors = []
        config_schema = app.get("config_schema", {})

        # Check required fields
        for field_name, field_schema in config_schema.items():
            if field_schema.get("required", False):
                if field_name not in config or config[field_name] is None:
                    errors.append(f"Missing required field: {field_name}")

        return len(errors) == 0, errors


# Global singleton instance
_catalog: ServiceCatalog | None = None


def get_service_catalog() -> ServiceCatalog:
    """Get the global service catalog instance"""
    global _catalog
    if _catalog is None:
        _catalog = ServiceCatalog()
    return _catalog

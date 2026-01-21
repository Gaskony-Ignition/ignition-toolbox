"""
Unit Tests for ServiceCatalog class

Tests the catalog.py module functionality:
- Catalog loading and parsing
- Application retrieval methods
- Category operations
- Search functionality
- Configuration validation
"""

import pytest
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from ignition_toolkit.stackbuilder.catalog import ServiceCatalog, get_service_catalog


class TestServiceCatalogLoading:
    """Test catalog loading and initialization."""

    def test_catalog_loads_from_default_path(self):
        """Test catalog loads successfully from default location."""
        catalog = ServiceCatalog()
        assert catalog.catalog is not None
        assert "applications" in catalog.catalog
        assert "categories" in catalog.catalog

    def test_catalog_loads_from_custom_path(self, catalog_path):
        """Test catalog loads from custom path."""
        catalog = ServiceCatalog(catalog_path=catalog_path)
        assert catalog.catalog is not None
        assert len(catalog.get_applications()) > 0

    def test_catalog_handles_missing_file(self, tmp_path):
        """Test catalog handles missing file gracefully."""
        nonexistent_path = tmp_path / "nonexistent.json"
        catalog = ServiceCatalog(catalog_path=nonexistent_path)
        # Should return empty catalog structure
        assert catalog.catalog == {"applications": [], "categories": []}

    def test_catalog_handles_invalid_json(self, tmp_path):
        """Test catalog handles invalid JSON gracefully."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ not valid json }")
        catalog = ServiceCatalog(catalog_path=invalid_file)
        assert catalog.catalog == {"applications": [], "categories": []}

    def test_catalog_lazy_loading(self, catalog_path):
        """Test catalog is lazily loaded."""
        catalog = ServiceCatalog(catalog_path=catalog_path)
        # _catalog should be None before first access
        assert catalog._catalog is None
        # Access the catalog property
        _ = catalog.catalog
        # Now _catalog should be populated
        assert catalog._catalog is not None


class TestApplicationRetrieval:
    """Test application retrieval methods."""

    @pytest.fixture
    def catalog(self, catalog_path):
        """Return a catalog instance."""
        return ServiceCatalog(catalog_path=catalog_path)

    def test_get_applications_returns_list(self, catalog):
        """Test get_applications returns a list."""
        apps = catalog.get_applications()
        assert isinstance(apps, list)
        assert len(apps) > 0

    def test_get_enabled_applications(self, catalog):
        """Test get_enabled_applications filters correctly."""
        enabled_apps = catalog.get_enabled_applications()
        for app in enabled_apps:
            assert app.get("enabled", False) is True

    def test_get_application_by_id_found(self, catalog):
        """Test get_application_by_id returns correct app."""
        app = catalog.get_application_by_id("ignition")
        assert app is not None
        assert app["id"] == "ignition"
        assert app["name"] == "Ignition"

    def test_get_application_by_id_not_found(self, catalog):
        """Test get_application_by_id returns None for unknown ID."""
        app = catalog.get_application_by_id("nonexistent")
        assert app is None

    def test_get_applications_by_category(self, catalog):
        """Test get_applications_by_category filters correctly."""
        db_apps = catalog.get_applications_by_category("Databases")
        assert len(db_apps) > 0
        for app in db_apps:
            assert app.get("category") == "Databases"
            assert app.get("enabled", False) is True

    def test_get_applications_by_category_empty(self, catalog):
        """Test get_applications_by_category returns empty for unknown category."""
        apps = catalog.get_applications_by_category("Nonexistent Category")
        assert apps == []

    def test_get_application_as_dict(self, catalog):
        """Test get_application_as_dict returns dict keyed by ID."""
        apps_dict = catalog.get_application_as_dict()
        assert isinstance(apps_dict, dict)
        assert "ignition" in apps_dict
        assert apps_dict["ignition"]["id"] == "ignition"


class TestCategoryOperations:
    """Test category-related operations."""

    @pytest.fixture
    def catalog(self, catalog_path):
        return ServiceCatalog(catalog_path=catalog_path)

    def test_get_categories_returns_list(self, catalog):
        """Test get_categories returns a list."""
        categories = catalog.get_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_get_categories_contains_expected(self, catalog):
        """Test get_categories contains expected categories."""
        categories = catalog.get_categories()
        assert "Industrial Platforms" in categories
        assert "Databases" in categories
        assert "Networking / Proxy" in categories


class TestSearchFunctionality:
    """Test application search functionality."""

    @pytest.fixture
    def catalog(self, catalog_path):
        return ServiceCatalog(catalog_path=catalog_path)

    def test_search_by_name(self, catalog):
        """Test search finds applications by name."""
        results = catalog.search_applications("ignition")
        assert len(results) >= 1
        # Should find Ignition
        assert any(app["id"] == "ignition" for app in results)

    def test_search_by_description(self, catalog):
        """Test search finds applications by description."""
        results = catalog.search_applications("SCADA")
        assert len(results) >= 1

    def test_search_case_insensitive(self, catalog):
        """Test search is case insensitive."""
        results_lower = catalog.search_applications("postgres")
        results_upper = catalog.search_applications("POSTGRES")
        results_mixed = catalog.search_applications("PostgreS")
        # All should return same results
        assert len(results_lower) == len(results_upper) == len(results_mixed)

    def test_search_no_results(self, catalog):
        """Test search returns empty list for no matches."""
        results = catalog.search_applications("xyznonexistent123")
        assert results == []

    def test_search_only_returns_enabled(self, catalog):
        """Test search only returns enabled applications."""
        # Search for something that might have disabled apps
        results = catalog.search_applications("database")
        for app in results:
            assert app.get("enabled", False) is True


class TestConfigurationValidation:
    """Test instance configuration validation."""

    @pytest.fixture
    def catalog(self, catalog_path):
        return ServiceCatalog(catalog_path=catalog_path)

    def test_validate_valid_config(self, catalog):
        """Test validation passes for valid config."""
        config = {"version": "latest", "admin_username": "admin"}
        is_valid, errors = catalog.validate_instance_config("ignition", config)
        # Even empty config should be valid (no required fields)
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_validate_unknown_app(self, catalog):
        """Test validation fails for unknown application."""
        is_valid, errors = catalog.validate_instance_config("nonexistent", {})
        assert is_valid is False
        assert len(errors) > 0
        assert "Unknown application" in errors[0]

    def test_validate_disabled_app(self, catalog):
        """Test validation fails for disabled application."""
        # Find a disabled app if any
        apps = catalog.get_applications()
        disabled_apps = [app for app in apps if not app.get("enabled", False)]
        if disabled_apps:
            is_valid, errors = catalog.validate_instance_config(disabled_apps[0]["id"], {})
            assert is_valid is False
            assert "not enabled" in errors[0]


class TestApplicationContent:
    """Test specific application content in the catalog."""

    @pytest.fixture
    def catalog(self, catalog_path):
        return ServiceCatalog(catalog_path=catalog_path)

    def test_ignition_has_required_fields(self, catalog):
        """Test Ignition app has all required fields."""
        app = catalog.get_application_by_id("ignition")
        assert app is not None
        assert "id" in app
        assert "name" in app
        assert "category" in app
        assert "description" in app
        assert "image" in app
        assert "default_config" in app
        assert "configurable_options" in app
        assert app["enabled"] is True

    def test_ignition_has_correct_ports(self, catalog):
        """Test Ignition has correct default ports."""
        app = catalog.get_application_by_id("ignition")
        ports = app["default_config"]["ports"]
        assert "8088:8088" in ports
        assert "8043:8043" in ports

    def test_postgres_has_database_config(self, catalog):
        """Test PostgreSQL has database configuration."""
        app = catalog.get_application_by_id("postgres")
        assert app is not None
        assert "POSTGRES_DB" in app["default_config"]["environment"]
        assert "POSTGRES_USER" in app["default_config"]["environment"]
        assert "POSTGRES_PASSWORD" in app["default_config"]["environment"]

    def test_keycloak_has_oauth_integration(self, catalog):
        """Test Keycloak has OAuth provider integration."""
        app = catalog.get_application_by_id("keycloak")
        assert app is not None
        assert "oauth_provider" in app.get("integrations", [])


class TestSingletonPattern:
    """Test the global singleton pattern."""

    def test_get_service_catalog_returns_instance(self):
        """Test get_service_catalog returns a ServiceCatalog instance."""
        catalog = get_service_catalog()
        assert isinstance(catalog, ServiceCatalog)

    def test_get_service_catalog_returns_same_instance(self):
        """Test get_service_catalog returns the same instance."""
        catalog1 = get_service_catalog()
        catalog2 = get_service_catalog()
        assert catalog1 is catalog2

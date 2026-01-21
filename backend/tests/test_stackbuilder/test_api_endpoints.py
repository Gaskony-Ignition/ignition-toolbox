"""
API Endpoint Tests for Stack Builder

Tests all endpoints in the stackbuilder.py router:
- GET /api/stackbuilder/catalog
- GET /api/stackbuilder/catalog/applications
- GET /api/stackbuilder/catalog/categories
- GET /api/stackbuilder/catalog/applications/{app_id}
- GET /api/stackbuilder/versions/{app_id}
- POST /api/stackbuilder/detect-integrations
- POST /api/stackbuilder/generate
- POST /api/stackbuilder/download
- CRUD operations for saved stacks
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from ignition_toolkit.api.routers.stackbuilder import (
    router,
    StackConfig,
    InstanceConfig,
    GlobalSettingsRequest,
    IntegrationSettingsRequest,
    SavedStackCreate,
    VALID_NAME_PATTERN,
    RESERVED_NAMES,
)


# Create a test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestCatalogEndpoints:
    """Test catalog-related endpoints."""

    def test_get_catalog(self):
        """Test GET /api/stackbuilder/catalog returns full catalog."""
        response = client.get("/api/stackbuilder/catalog")
        assert response.status_code == 200
        data = response.json()
        assert "applications" in data
        assert "categories" in data
        assert len(data["applications"]) > 0

    def test_get_applications(self):
        """Test GET /api/stackbuilder/catalog/applications returns enabled apps."""
        response = client.get("/api/stackbuilder/catalog/applications")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned apps should be enabled
        for app in data:
            assert app.get("enabled", False) is True

    def test_get_categories(self):
        """Test GET /api/stackbuilder/catalog/categories returns categories."""
        response = client.get("/api/stackbuilder/catalog/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "Industrial Platforms" in data
        assert "Databases" in data

    def test_get_application_by_id_success(self):
        """Test GET /api/stackbuilder/catalog/applications/{app_id} with valid ID."""
        response = client.get("/api/stackbuilder/catalog/applications/ignition")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "ignition"
        assert data["name"] == "Ignition"
        assert "image" in data

    def test_get_application_by_id_not_found(self):
        """Test GET /api/stackbuilder/catalog/applications/{app_id} with invalid ID."""
        response = client.get("/api/stackbuilder/catalog/applications/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_ignition_versions(self):
        """Test GET /api/stackbuilder/versions/ignition returns version list."""
        with patch('ignition_toolkit.api.routers.stackbuilder._get_ignition_versions') as mock_versions:
            mock_versions.return_value = ["latest", "8.3.2", "8.3.1", "8.1.45"]
            response = client.get("/api/stackbuilder/versions/ignition")
            assert response.status_code == 200
            data = response.json()
            assert "versions" in data
            assert "latest" in data["versions"]

    def test_get_postgres_versions(self):
        """Test GET /api/stackbuilder/versions/postgres returns version list."""
        with patch('ignition_toolkit.api.routers.stackbuilder._get_postgres_versions') as mock_versions:
            mock_versions.return_value = ["latest", "16-alpine", "15-alpine"]
            response = client.get("/api/stackbuilder/versions/postgres")
            assert response.status_code == 200
            data = response.json()
            assert "versions" in data

    def test_get_versions_unknown_app(self):
        """Test GET /api/stackbuilder/versions/{app_id} with unknown app returns fallback."""
        response = client.get("/api/stackbuilder/versions/unknownapp")
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        # Should return at least "latest" as fallback
        assert "latest" in data["versions"]


class TestIntegrationDetection:
    """Test integration detection endpoint."""

    def test_detect_integrations_basic(self, sample_ignition_instance, sample_postgres_instance):
        """Test POST /api/stackbuilder/detect-integrations with basic stack."""
        stack_config = {
            "instances": [sample_ignition_instance, sample_postgres_instance],
            "global_settings": {"stack_name": "test-stack", "timezone": "UTC"},
        }
        response = client.post("/api/stackbuilder/detect-integrations", json=stack_config)
        assert response.status_code == 200
        data = response.json()
        assert "integrations" in data
        assert "conflicts" in data
        assert "warnings" in data
        assert "recommendations" in data
        assert "summary" in data

    def test_detect_integrations_with_oauth(
        self, sample_ignition_instance, sample_keycloak_instance, sample_grafana_instance
    ):
        """Test integration detection with OAuth provider."""
        stack_config = {
            "instances": [
                sample_ignition_instance,
                sample_keycloak_instance,
                sample_grafana_instance,
            ],
        }
        response = client.post("/api/stackbuilder/detect-integrations", json=stack_config)
        assert response.status_code == 200
        data = response.json()
        # Should detect OAuth integration
        assert "oauth_provider" in data["integrations"]

    def test_detect_integrations_conflict(self, sample_traefik_instance):
        """Test integration detection identifies conflicts."""
        nginx_instance = {
            "app_id": "nginx-proxy-manager",
            "instance_name": "nginx",
            "config": {},
        }
        stack_config = {
            "instances": [sample_traefik_instance, nginx_instance],
        }
        response = client.post("/api/stackbuilder/detect-integrations", json=stack_config)
        assert response.status_code == 200
        data = response.json()
        # Should detect reverse proxy conflict
        assert len(data["conflicts"]) > 0

    def test_detect_integrations_empty_instances(self):
        """Test integration detection with empty instance list."""
        stack_config = {"instances": []}
        response = client.post("/api/stackbuilder/detect-integrations", json=stack_config)
        assert response.status_code == 200
        data = response.json()
        assert data["integrations"] == {}
        assert data["conflicts"] == []


class TestStackGeneration:
    """Test stack generation endpoints."""

    def test_generate_basic_stack(self, sample_ignition_instance, sample_postgres_instance):
        """Test POST /api/stackbuilder/generate with basic stack."""
        stack_config = {
            "instances": [sample_ignition_instance, sample_postgres_instance],
            "global_settings": {
                "stack_name": "test-stack",
                "timezone": "UTC",
                "restart_policy": "unless-stopped",
            },
        }
        response = client.post("/api/stackbuilder/generate", json=stack_config)
        assert response.status_code == 200
        data = response.json()
        assert "docker_compose" in data
        assert "env" in data
        assert "readme" in data
        assert "config_files" in data
        # Verify YAML content
        assert "name: test-stack" in data["docker_compose"]
        assert "ignition-gateway" in data["docker_compose"]
        assert "postgres-db" in data["docker_compose"]

    def test_generate_stack_with_traefik(
        self, sample_ignition_instance, sample_traefik_instance
    ):
        """Test stack generation with Traefik reverse proxy."""
        stack_config = {
            "instances": [sample_ignition_instance, sample_traefik_instance],
            "global_settings": {"stack_name": "proxy-stack"},
            "integration_settings": {
                "reverse_proxy": {
                    "base_domain": "example.com",
                    "enable_https": False,
                }
            },
        }
        response = client.post("/api/stackbuilder/generate", json=stack_config)
        assert response.status_code == 200
        data = response.json()
        # Should include Traefik labels
        assert "traefik" in data["docker_compose"].lower()
        # Should include Traefik config files
        assert any("traefik" in path for path in data["config_files"].keys())

    def test_generate_stack_with_keycloak_oauth(
        self, sample_ignition_instance, sample_keycloak_instance, sample_grafana_instance
    ):
        """Test stack generation with Keycloak OAuth integration."""
        stack_config = {
            "instances": [
                sample_ignition_instance,
                sample_keycloak_instance,
                sample_grafana_instance,
            ],
            "global_settings": {"stack_name": "oauth-stack"},
            "integration_settings": {
                "oauth": {
                    "realm_name": "test-realm",
                    "auto_configure_services": True,
                }
            },
        }
        response = client.post("/api/stackbuilder/generate", json=stack_config)
        assert response.status_code == 200
        data = response.json()
        # Should include Keycloak realm config
        assert any("keycloak" in path for path in data["config_files"].keys())

    def test_download_stack_returns_zip(self, sample_ignition_instance, sample_postgres_instance):
        """Test POST /api/stackbuilder/download returns ZIP file."""
        stack_config = {
            "instances": [sample_ignition_instance, sample_postgres_instance],
            "global_settings": {"stack_name": "download-test"},
        }
        response = client.post("/api/stackbuilder/download", json=stack_config)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "download-test.zip" in response.headers.get("content-disposition", "")
        # Verify it's a valid ZIP (starts with PK signature)
        assert response.content[:2] == b"PK"


class TestSavedStacksCRUD:
    """Test saved stacks CRUD operations."""

    @pytest.fixture(autouse=True)
    def mock_database_operations(self):
        """Mock database operations for saved stack tests."""
        with patch('ignition_toolkit.api.routers.stackbuilder.get_database') as mock_get_db:
            mock_session = MagicMock()
            mock_db = MagicMock()
            mock_db.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_db.session_scope.return_value.__exit__ = MagicMock(return_value=None)
            mock_get_db.return_value = mock_db
            self.mock_session = mock_session
            self.mock_db = mock_db
            yield

    def test_list_saved_stacks(self):
        """Test GET /api/stackbuilder/stacks returns list."""
        mock_stack = MagicMock()
        mock_stack.to_dict.return_value = {
            "id": 1,
            "stack_name": "test-stack",
            "description": "Test",
            "config_json": {},
            "global_settings": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        self.mock_session.query.return_value.order_by.return_value.all.return_value = [mock_stack]

        response = client.get("/api/stackbuilder/stacks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_save_stack(self):
        """Test POST /api/stackbuilder/stacks creates new stack."""
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_stack = MagicMock()
        mock_stack.to_dict.return_value = {
            "id": 1,
            "stack_name": "new-stack",
            "description": "A new stack",
            "config_json": {"instances": []},
            "global_settings": {"timezone": "UTC"},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }

        # Mock SavedStackModel constructor
        with patch('ignition_toolkit.api.routers.stackbuilder.SavedStackModel') as MockModel:
            MockModel.return_value = mock_stack

            stack_data = {
                "stack_name": "new-stack",
                "description": "A new stack",
                "config_json": {"instances": []},
                "global_settings": {"timezone": "UTC"},
            }
            response = client.post("/api/stackbuilder/stacks", json=stack_data)
            # Should succeed with 200 (response_model converts to JSON)
            assert response.status_code == 200

    def test_save_stack_duplicate_name(self):
        """Test POST /api/stackbuilder/stacks rejects duplicate name."""
        # Mock existing stack found
        existing_stack = MagicMock()
        existing_stack.stack_name = "existing-stack"
        self.mock_session.query.return_value.filter.return_value.first.return_value = existing_stack

        stack_data = {
            "stack_name": "existing-stack",
            "description": "Duplicate",
            "config_json": {},
        }
        response = client.post("/api/stackbuilder/stacks", json=stack_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_get_saved_stack_by_id(self):
        """Test GET /api/stackbuilder/stacks/{stack_id} returns stack."""
        mock_stack = MagicMock()
        mock_stack.to_dict.return_value = {
            "id": 1,
            "stack_name": "test-stack",
            "description": "Test",
            "config_json": {},
            "global_settings": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_stack

        response = client.get("/api/stackbuilder/stacks/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    def test_get_saved_stack_not_found(self):
        """Test GET /api/stackbuilder/stacks/{stack_id} returns 404."""
        self.mock_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/api/stackbuilder/stacks/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_saved_stack(self):
        """Test DELETE /api/stackbuilder/stacks/{stack_id} deletes stack."""
        mock_stack = MagicMock()
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_stack

        response = client.delete("/api/stackbuilder/stacks/1")
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    def test_delete_saved_stack_not_found(self):
        """Test DELETE /api/stackbuilder/stacks/{stack_id} returns 404."""
        self.mock_session.query.return_value.filter.return_value.first.return_value = None

        response = client.delete("/api/stackbuilder/stacks/999")
        assert response.status_code == 404


class TestDockerInstallerDownloads:
    """Test Docker installer download endpoints."""

    def test_download_linux_installer(self):
        """Test GET /api/stackbuilder/download/docker-installer/linux."""
        response = client.get("/api/stackbuilder/download/docker-installer/linux")
        assert response.status_code == 200
        assert "install-docker-linux.sh" in response.headers.get("content-disposition", "")
        content = response.content.decode()
        assert "#!/bin/bash" in content
        assert "docker" in content.lower()

    def test_download_windows_installer(self):
        """Test GET /api/stackbuilder/download/docker-installer/windows."""
        response = client.get("/api/stackbuilder/download/docker-installer/windows")
        assert response.status_code == 200
        assert "install-docker-windows.ps1" in response.headers.get("content-disposition", "")
        content = response.content.decode()
        assert "docker" in content.lower()


class TestOfflineBundleGeneration:
    """Test offline bundle generation endpoint."""

    def test_generate_offline_bundle(self, sample_ignition_instance, sample_postgres_instance):
        """Test POST /api/stackbuilder/generate-offline-bundle returns ZIP."""
        stack_config = {
            "instances": [sample_ignition_instance, sample_postgres_instance],
            "global_settings": {"stack_name": "offline-test"},
        }
        response = client.post("/api/stackbuilder/generate-offline-bundle", json=stack_config)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "offline-test-offline.zip" in response.headers.get("content-disposition", "")
        # Verify it's a valid ZIP
        assert response.content[:2] == b"PK"

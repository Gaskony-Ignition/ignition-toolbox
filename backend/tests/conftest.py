"""
Pytest configuration and shared fixtures.

Global fixtures (available to all test modules):
  - mock_db          : mock database with working session_scope context manager
  - mock_app_services: mock app.state.services (execution manager, websocket manager)
  - sample_playbook_yaml: minimal valid playbook YAML string

Stack Builder fixtures:
  - catalog_path, integrations_path, sample_*_instance, basic/full_stack_instances
"""

import pytest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add the backend directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def catalog_path():
    """Return the path to the catalog.json file."""
    return Path(__file__).parent.parent / "ignition_toolkit" / "stackbuilder" / "data" / "catalog.json"


@pytest.fixture
def integrations_path():
    """Return the path to the integrations.json file."""
    return Path(__file__).parent.parent / "ignition_toolkit" / "stackbuilder" / "data" / "integrations.json"


@pytest.fixture
def sample_ignition_instance():
    """Return a sample Ignition instance configuration."""
    return {
        "app_id": "ignition",
        "instance_name": "ignition-gateway",
        "config": {
            "version": "8.3.2",
            "http_port": 8088,
            "https_port": 8043,
            "admin_username": "admin",
            "admin_password": "password",
            "edition": "standard",
        }
    }


@pytest.fixture
def sample_postgres_instance():
    """Return a sample PostgreSQL instance configuration."""
    return {
        "app_id": "postgres",
        "instance_name": "postgres-db",
        "config": {
            "version": "16-alpine",
            "port": 5432,
            "database": "ignition_db",
            "username": "postgres",
            "password": "postgres123",
        }
    }


@pytest.fixture
def sample_traefik_instance():
    """Return a sample Traefik instance configuration."""
    return {
        "app_id": "traefik",
        "instance_name": "traefik",
        "config": {
            "version": "latest",
            "http_port": 80,
            "https_port": 443,
            "dashboard_port": 8080,
        }
    }


@pytest.fixture
def sample_keycloak_instance():
    """Return a sample Keycloak instance configuration."""
    return {
        "app_id": "keycloak",
        "instance_name": "keycloak",
        "config": {
            "version": "latest",
            "port": 8180,
            "admin_username": "admin",
            "admin_password": "admin123",
        }
    }


@pytest.fixture
def sample_mosquitto_instance():
    """Return a sample Mosquitto instance configuration."""
    return {
        "app_id": "mosquitto",
        "instance_name": "mqtt-broker",
        "config": {
            "version": "latest",
            "mqtt_port": 1883,
            "websocket_port": 9001,
        }
    }


@pytest.fixture
def sample_grafana_instance():
    """Return a sample Grafana instance configuration."""
    return {
        "app_id": "grafana",
        "instance_name": "grafana",
        "config": {
            "version": "latest",
            "port": 3000,
            "admin_username": "admin",
            "admin_password": "grafana123",
        }
    }


@pytest.fixture
def sample_mailhog_instance():
    """Return a sample MailHog instance configuration."""
    return {
        "app_id": "mailhog",
        "instance_name": "mailhog",
        "config": {
            "version": "latest",
            "smtp_port": 1025,
            "http_port": 8025,
        }
    }


@pytest.fixture
def basic_stack_instances(sample_ignition_instance, sample_postgres_instance):
    """Return a basic stack with Ignition and PostgreSQL."""
    return [sample_ignition_instance, sample_postgres_instance]


@pytest.fixture
def full_stack_instances(
    sample_ignition_instance,
    sample_postgres_instance,
    sample_traefik_instance,
    sample_keycloak_instance,
    sample_grafana_instance,
):
    """Return a full stack with multiple services."""
    return [
        sample_ignition_instance,
        sample_postgres_instance,
        sample_traefik_instance,
        sample_keycloak_instance,
        sample_grafana_instance,
    ]


@pytest.fixture
def mock_database():
    """Return a mock database for API tests."""
    db = MagicMock()
    db.session_scope.return_value.__enter__ = MagicMock()
    db.session_scope.return_value.__exit__ = MagicMock()
    return db


# ============================================================================
# Global shared fixtures (used across test_api/, test_playbook/, etc.)
# ============================================================================


@pytest.fixture
def mock_db():
    """
    Mock database with a working contextmanager-based session_scope.

    The session returns None for all .first() queries by default (simulates
    empty database). Override specific queries in individual tests as needed.

    Usage::

        def test_something(mock_db):
            with patch("my.module.get_database", return_value=mock_db):
                result = asyncio.run(my_endpoint())
    """
    db = MagicMock()
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter_by.return_value.first.return_value = None
    session.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
    session.query.return_value.all.return_value = []

    @contextmanager
    def session_scope():
        yield session

    db.session_scope = session_scope
    db._session = session  # expose for per-test customisation
    return db


@pytest.fixture
def mock_app_services():
    """
    Mock app.state.services and install it on the FastAPI app.

    Provides:
      - execution_manager.get_engine()      → None (not found)
      - execution_manager.cancel_execution() → None (not in memory)
      - websocket_manager.broadcast_*()     → no-op async

    Cleans up after the test.

    Usage::

        def test_something(mock_app_services):
            # app.state.services is set automatically
            result = asyncio.run(some_endpoint("id"))
    """
    from ignition_toolkit.api.app import app

    svc = MagicMock()
    svc.execution_manager.get_engine.return_value = None
    svc.execution_manager.cancel_execution = AsyncMock(return_value=None)
    svc.websocket_manager.broadcast_execution_state = AsyncMock()
    svc.websocket_manager.broadcast_json = AsyncMock()

    app.state.services = svc
    yield svc

    try:
        del app.state.services
    except AttributeError:
        pass


@pytest.fixture
def sample_playbook_yaml() -> str:
    """Minimal valid playbook YAML for use in API and schema tests."""
    return """\
name: Test Playbook
version: "1.0"
description: A minimal playbook for testing
domain: gateway
steps:
  - id: step1
    name: Log a message
    type: utility.log
    parameters:
      message: "hello"
      level: info
"""

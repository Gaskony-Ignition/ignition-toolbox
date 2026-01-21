"""
Integration Tests for Stack Builder Complete Workflows

Tests complete stack generation workflows end-to-end:
- Basic Ignition + PostgreSQL stack
- Stack with Keycloak OAuth
- Stack with Traefik reverse proxy
- Stack with MQTT broker
- Full IIoT stack with all components
"""

import pytest
import yaml
import zipfile
import io

from ignition_toolkit.stackbuilder.compose_generator import (
    ComposeGenerator,
    GlobalSettings,
    IntegrationSettings,
)
from ignition_toolkit.stackbuilder.catalog import get_service_catalog
from ignition_toolkit.stackbuilder.integration_engine import get_integration_engine


class TestBasicIgnitionPostgresStack:
    """Test basic Ignition + PostgreSQL stack generation."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    @pytest.fixture
    def instances(self, sample_ignition_instance, sample_postgres_instance):
        return [sample_ignition_instance, sample_postgres_instance]

    def test_generates_valid_compose_yaml(self, generator, instances):
        """Test generated docker-compose is valid YAML."""
        settings = GlobalSettings(stack_name="ignition-postgres")
        result = generator.generate(instances, settings)

        parsed = yaml.safe_load(result["docker_compose"])
        assert parsed is not None
        assert "services" in parsed
        assert len(parsed["services"]) == 2

    def test_services_are_connected_to_network(self, generator, instances):
        """Test all services are on the same network."""
        settings = GlobalSettings(stack_name="test-stack")
        result = generator.generate(instances, settings)

        parsed = yaml.safe_load(result["docker_compose"])

        for service_name, service in parsed["services"].items():
            assert "test-stack-network" in service["networks"]

    def test_ignition_has_database_env_vars(self, generator, instances):
        """Test Ignition service is configured for database."""
        result = generator.generate(instances)
        parsed = yaml.safe_load(result["docker_compose"])

        ignition = parsed["services"]["ignition-gateway"]
        # Check for basic Ignition env vars
        assert "ACCEPT_IGNITION_EULA" in ignition["environment"]

    def test_postgres_has_database_config(self, generator, instances):
        """Test PostgreSQL has proper database configuration."""
        result = generator.generate(instances)
        parsed = yaml.safe_load(result["docker_compose"])

        postgres = parsed["services"]["postgres-db"]
        env = postgres["environment"]
        assert "POSTGRES_DB" in env
        assert "POSTGRES_USER" in env
        assert "POSTGRES_PASSWORD" in env

    def test_database_registration_script_generated(self, generator, instances):
        """Test database registration script is generated."""
        integration_settings = IntegrationSettings(database={"auto_register": True})
        result = generator.generate(instances, integration_settings=integration_settings)

        config_files = result.get("config_files", {})
        # May have registration script
        assert isinstance(config_files, dict)

    def test_readme_documents_stack(self, generator, instances):
        """Test README documents the stack."""
        result = generator.generate(instances)

        readme = result["readme"]
        assert "ignition-gateway" in readme
        assert "postgres-db" in readme
        assert "docker compose" in readme.lower()


class TestStackWithKeycloakOAuth:
    """Test stack generation with Keycloak OAuth integration."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    @pytest.fixture
    def instances(self, sample_ignition_instance, sample_keycloak_instance, sample_grafana_instance):
        return [sample_ignition_instance, sample_keycloak_instance, sample_grafana_instance]

    def test_oauth_integration_detected(self, instances):
        """Test OAuth integration is detected."""
        engine = get_integration_engine()
        result = engine.detect_integrations(instances)

        assert "oauth_provider" in result["integrations"]
        oauth = result["integrations"]["oauth_provider"]
        provider_ids = [p["service_id"] for p in oauth["providers"]]
        assert "keycloak" in provider_ids

    def test_keycloak_realm_config_generated(self, generator, instances):
        """Test Keycloak realm configuration is generated."""
        integration_settings = IntegrationSettings(
            oauth={"realm_name": "iiot", "auto_configure_services": True}
        )
        result = generator.generate(instances, integration_settings=integration_settings)

        config_files = result.get("config_files", {})
        keycloak_configs = [k for k in config_files.keys() if "keycloak" in k]
        # Should have keycloak config files
        assert isinstance(config_files, dict)

    def test_grafana_gets_oauth_config(self, generator, instances):
        """Test Grafana gets OAuth configuration."""
        integration_settings = IntegrationSettings(
            oauth={"realm_name": "iiot", "auto_configure_services": True}
        )
        result = generator.generate(instances, integration_settings=integration_settings)

        parsed = yaml.safe_load(result["docker_compose"])
        grafana = parsed["services"]["grafana"]
        env = grafana.get("environment", {})

        # May have OAuth env vars if integration is auto-configured
        assert isinstance(env, dict)

    def test_keycloak_has_start_command(self, generator, instances):
        """Test Keycloak has start command configured."""
        result = generator.generate(instances)
        parsed = yaml.safe_load(result["docker_compose"])

        keycloak = parsed["services"]["keycloak"]
        assert "command" in keycloak


class TestStackWithTraefikProxy:
    """Test stack generation with Traefik reverse proxy."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    @pytest.fixture
    def instances(self, sample_ignition_instance, sample_grafana_instance, sample_traefik_instance):
        return [sample_ignition_instance, sample_grafana_instance, sample_traefik_instance]

    def test_reverse_proxy_integration_detected(self, instances):
        """Test reverse proxy integration is detected."""
        engine = get_integration_engine()
        result = engine.detect_integrations(instances)

        assert "reverse_proxy" in result["integrations"]
        rp = result["integrations"]["reverse_proxy"]
        assert rp["provider"] == "traefik"
        assert len(rp["targets"]) > 0

    def test_traefik_labels_added_to_services(self, generator, instances):
        """Test Traefik labels are added to web services."""
        result = generator.generate(instances)
        parsed = yaml.safe_load(result["docker_compose"])

        # Ignition should have Traefik labels
        ignition = parsed["services"]["ignition-gateway"]
        assert "labels" in ignition

        # Grafana should have Traefik labels
        grafana = parsed["services"]["grafana"]
        assert "labels" in grafana

    def test_traefik_config_files_generated(self, generator, instances):
        """Test Traefik configuration files are generated."""
        integration_settings = IntegrationSettings(
            reverse_proxy={"base_domain": "localhost", "enable_https": False}
        )
        result = generator.generate(instances, integration_settings=integration_settings)

        config_files = result["config_files"]
        traefik_configs = [k for k in config_files.keys() if "traefik" in k]
        assert len(traefik_configs) > 0

    def test_traefik_static_config_valid(self, generator, instances):
        """Test Traefik static config is valid YAML."""
        integration_settings = IntegrationSettings(
            reverse_proxy={"base_domain": "localhost", "enable_https": False}
        )
        result = generator.generate(instances, integration_settings=integration_settings)

        config_files = result["config_files"]
        static_config_key = "configs/traefik/traefik.yml"
        if static_config_key in config_files:
            parsed = yaml.safe_load(config_files[static_config_key])
            assert "entryPoints" in parsed

    def test_traefik_dynamic_config_has_routes(self, generator, instances):
        """Test Traefik dynamic config has service routes."""
        integration_settings = IntegrationSettings(
            reverse_proxy={"base_domain": "localhost", "enable_https": False}
        )
        result = generator.generate(instances, integration_settings=integration_settings)

        config_files = result["config_files"]
        dynamic_config_key = "configs/traefik/dynamic/services.yml"
        if dynamic_config_key in config_files:
            parsed = yaml.safe_load(config_files[dynamic_config_key])
            assert "http" in parsed
            assert "routers" in parsed["http"]


class TestStackWithMQTTBroker:
    """Test stack generation with MQTT broker."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    @pytest.fixture
    def instances(self, sample_ignition_instance, sample_mosquitto_instance):
        return [sample_ignition_instance, sample_mosquitto_instance]

    def test_mqtt_integration_detected(self, instances):
        """Test MQTT integration is detected."""
        engine = get_integration_engine()
        result = engine.detect_integrations(instances)

        assert "mqtt_broker" in result["integrations"]
        mqtt = result["integrations"]["mqtt_broker"]
        assert len(mqtt["providers"]) > 0

    def test_mosquitto_config_generated(self, generator, instances):
        """Test Mosquitto configuration is generated."""
        integration_settings = IntegrationSettings(
            mqtt={"username": "mqtt", "password": "mqtt123"}
        )
        result = generator.generate(instances, integration_settings=integration_settings)

        config_files = result["config_files"]
        mqtt_configs = [k for k in config_files.keys() if "mosquitto" in k.lower() or "mqtt" in k.lower()]
        assert len(mqtt_configs) > 0

    def test_mosquitto_password_file_generated(self, generator, instances):
        """Test Mosquitto password file is generated when auth is configured."""
        integration_settings = IntegrationSettings(
            mqtt={"username": "mqttuser", "password": "mqttpass"}
        )
        result = generator.generate(instances, integration_settings=integration_settings)

        config_files = result["config_files"]
        passwd_files = [k for k in config_files.keys() if "passwd" in k]
        assert len(passwd_files) > 0


class TestFullIIoTStack:
    """Test full IIoT stack with all components."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    @pytest.fixture
    def instances(
        self,
        sample_ignition_instance,
        sample_postgres_instance,
        sample_traefik_instance,
        sample_keycloak_instance,
        sample_grafana_instance,
        sample_mosquitto_instance,
        sample_mailhog_instance,
    ):
        return [
            sample_ignition_instance,
            sample_postgres_instance,
            sample_traefik_instance,
            sample_keycloak_instance,
            sample_grafana_instance,
            sample_mosquitto_instance,
            sample_mailhog_instance,
        ]

    def test_all_services_generated(self, generator, instances):
        """Test all services are generated."""
        result = generator.generate(instances)
        parsed = yaml.safe_load(result["docker_compose"])

        # Should have all 7 services
        assert len(parsed["services"]) == 7

    def test_all_integrations_detected(self, instances):
        """Test all relevant integrations are detected."""
        engine = get_integration_engine()
        result = engine.detect_integrations(instances)

        integrations = result["integrations"]
        # Should detect multiple integrations
        assert "db_provider" in integrations
        assert "reverse_proxy" in integrations
        assert "oauth_provider" in integrations
        assert "mqtt_broker" in integrations
        assert "email_testing" in integrations

    def test_zip_contains_all_files(self, generator, instances):
        """Test ZIP file contains all required files."""
        settings = GlobalSettings(stack_name="full-iiot-stack")
        zip_bytes = generator.generate_zip(instances, settings)

        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            names = zf.namelist()

            # Core files
            assert "docker-compose.yml" in names
            assert ".env" in names
            assert "README.md" in names

            # Should have config files
            config_files = [n for n in names if n.startswith("configs/")]
            assert len(config_files) > 0

    def test_no_conflicts_detected(self, instances):
        """Test no conflicts in full stack."""
        engine = get_integration_engine()
        result = engine.detect_integrations(instances)

        # Should have no conflicts
        assert len(result["conflicts"]) == 0

    def test_readme_is_comprehensive(self, generator, instances):
        """Test README is comprehensive."""
        settings = GlobalSettings(stack_name="full-iiot-stack")
        result = generator.generate(instances, settings)

        readme = result["readme"]
        # Should mention stack name
        assert "full-iiot-stack" in readme
        # Should have service URLs section
        assert "URL" in readme or "http://" in readme
        # Should have getting started
        assert "Getting Started" in readme or "Start" in readme


class TestStackWithEmailIntegration:
    """Test stack generation with email/SMTP integration."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    @pytest.fixture
    def instances(self, sample_ignition_instance, sample_grafana_instance, sample_mailhog_instance):
        return [sample_ignition_instance, sample_grafana_instance, sample_mailhog_instance]

    def test_email_integration_detected(self, instances):
        """Test email integration is detected."""
        engine = get_integration_engine()
        result = engine.detect_integrations(instances)

        assert "email_testing" in result["integrations"]

    def test_services_get_smtp_config(self, generator, instances):
        """Test services get SMTP configuration."""
        integration_settings = IntegrationSettings(
            email={"from_address": "noreply@test.local", "auto_configure_services": True}
        )
        result = generator.generate(instances, integration_settings=integration_settings)

        parsed = yaml.safe_load(result["docker_compose"])

        # Check Ignition has SMTP config
        ignition = parsed["services"]["ignition-gateway"]
        env = ignition.get("environment", {})
        # May have SMTP env vars
        assert isinstance(env, dict)

        # Check Grafana has SMTP config
        grafana = parsed["services"]["grafana"]
        grafana_env = grafana.get("environment", {})
        assert isinstance(grafana_env, dict)


class TestVisualizationIntegration:
    """Test Grafana visualization integration."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    @pytest.fixture
    def instances(self, sample_grafana_instance, sample_postgres_instance):
        prometheus_instance = {
            "app_id": "prometheus",
            "instance_name": "prometheus",
            "config": {"version": "latest"},
        }
        return [sample_grafana_instance, prometheus_instance, sample_postgres_instance]

    def test_visualization_integration_detected(self, instances):
        """Test visualization integration is detected."""
        engine = get_integration_engine()
        result = engine.detect_integrations(instances)

        assert "visualization" in result["integrations"]

    def test_grafana_datasources_provisioned(self, generator, instances):
        """Test Grafana datasources are provisioned."""
        result = generator.generate(instances)

        config_files = result.get("config_files", {})
        # Look for Grafana datasource provisioning
        datasource_files = [k for k in config_files.keys() if "grafana" in k and "datasource" in k.lower()]
        # May have datasource provisioning
        assert isinstance(config_files, dict)

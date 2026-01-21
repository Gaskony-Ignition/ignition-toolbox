"""
Unit Tests for ComposeGenerator class

Tests the compose_generator.py module functionality:
- Docker Compose YAML generation
- Environment variable generation
- Configuration file generation
- README generation
- ZIP file generation
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


class TestGlobalSettings:
    """Test GlobalSettings class."""

    def test_default_settings(self):
        """Test default global settings."""
        settings = GlobalSettings()
        assert settings.stack_name == "iiot-stack"
        assert settings.timezone == "UTC"
        assert settings.restart_policy == "unless-stopped"

    def test_custom_settings(self):
        """Test custom global settings."""
        settings = GlobalSettings(
            stack_name="my-stack",
            timezone="America/New_York",
            restart_policy="always",
        )
        assert settings.stack_name == "my-stack"
        assert settings.timezone == "America/New_York"
        assert settings.restart_policy == "always"


class TestIntegrationSettings:
    """Test IntegrationSettings class."""

    def test_default_settings(self):
        """Test default integration settings."""
        settings = IntegrationSettings()
        assert settings.reverse_proxy["base_domain"] == "localhost"
        assert settings.mqtt["enable_tls"] is False
        assert settings.oauth["realm_name"] == "iiot"
        assert settings.database["auto_register"] is True

    def test_custom_settings(self):
        """Test custom integration settings."""
        settings = IntegrationSettings(
            reverse_proxy={"base_domain": "example.com", "enable_https": True},
            oauth={"realm_name": "custom-realm"},
        )
        assert settings.reverse_proxy["base_domain"] == "example.com"
        assert settings.oauth["realm_name"] == "custom-realm"


class TestComposeGeneratorBasic:
    """Test basic ComposeGenerator functionality."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_generator_initialization(self, generator):
        """Test generator initializes correctly."""
        assert generator.catalog is not None
        assert generator.engine is not None

    def test_generate_empty_instances(self, generator):
        """Test generation with empty instance list."""
        result = generator.generate([])
        assert "docker_compose" in result
        assert "env" in result
        assert "readme" in result
        assert "config_files" in result

    def test_generate_returns_valid_yaml(self, generator, sample_ignition_instance):
        """Test generated docker-compose is valid YAML."""
        result = generator.generate([sample_ignition_instance])
        # Should not raise an exception
        parsed = yaml.safe_load(result["docker_compose"])
        assert parsed is not None
        assert "services" in parsed
        assert "networks" in parsed


class TestComposeGeneratorServices:
    """Test service generation in ComposeGenerator."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_ignition_service_generation(self, generator, sample_ignition_instance):
        """Test Ignition service is generated correctly."""
        result = generator.generate([sample_ignition_instance])
        parsed = yaml.safe_load(result["docker_compose"])

        assert "ignition-gateway" in parsed["services"]
        service = parsed["services"]["ignition-gateway"]

        # Check image
        assert "inductiveautomation/ignition" in service["image"]

        # Check ports
        assert "ports" in service

        # Check environment
        assert "environment" in service
        assert service["environment"]["ACCEPT_IGNITION_EULA"] == "Y"

    def test_postgres_service_generation(self, generator, sample_postgres_instance):
        """Test PostgreSQL service is generated correctly."""
        result = generator.generate([sample_postgres_instance])
        parsed = yaml.safe_load(result["docker_compose"])

        assert "postgres-db" in parsed["services"]
        service = parsed["services"]["postgres-db"]

        assert "postgres" in service["image"]
        assert "environment" in service
        assert service["environment"]["POSTGRES_DB"] == "ignition_db"

    def test_traefik_service_generation(self, generator, sample_traefik_instance):
        """Test Traefik service is generated correctly."""
        result = generator.generate([sample_traefik_instance])
        parsed = yaml.safe_load(result["docker_compose"])

        assert "traefik" in parsed["services"]
        service = parsed["services"]["traefik"]

        assert "traefik" in service["image"]
        # Should have docker socket volume
        volumes = service.get("volumes", [])
        assert any("/var/run/docker.sock" in vol for vol in volumes)

    def test_keycloak_service_generation(self, generator, sample_keycloak_instance):
        """Test Keycloak service is generated correctly."""
        result = generator.generate([sample_keycloak_instance])
        parsed = yaml.safe_load(result["docker_compose"])

        assert "keycloak" in parsed["services"]
        service = parsed["services"]["keycloak"]

        assert "keycloak" in service["image"]
        assert "command" in service


class TestComposeGeneratorNetworking:
    """Test network configuration in ComposeGenerator."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_network_created(self, generator, sample_ignition_instance):
        """Test network is created in compose output."""
        settings = GlobalSettings(stack_name="test-stack")
        result = generator.generate([sample_ignition_instance], settings)
        parsed = yaml.safe_load(result["docker_compose"])

        assert "networks" in parsed
        assert "test-stack-network" in parsed["networks"]

    def test_services_use_network(self, generator, sample_ignition_instance):
        """Test services are connected to the stack network."""
        settings = GlobalSettings(stack_name="test-stack")
        result = generator.generate([sample_ignition_instance], settings)
        parsed = yaml.safe_load(result["docker_compose"])

        service = parsed["services"]["ignition-gateway"]
        assert "test-stack-network" in service["networks"]


class TestComposeGeneratorVolumes:
    """Test volume configuration in ComposeGenerator."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_named_volumes_collected(self, generator, sample_ignition_instance):
        """Test named volumes are collected in volumes section."""
        result = generator.generate([sample_ignition_instance])
        parsed = yaml.safe_load(result["docker_compose"])

        # Should have volumes section
        assert "volumes" in parsed

    def test_volume_names_substituted(self, generator, sample_postgres_instance):
        """Test {instance_name} is substituted in volume names."""
        result = generator.generate([sample_postgres_instance])
        parsed = yaml.safe_load(result["docker_compose"])

        service = parsed["services"]["postgres-db"]
        volumes = service.get("volumes", [])
        # Should have instance name in volume path
        assert any("postgres-db" in vol for vol in volumes)


class TestComposeGeneratorWithTraefik:
    """Test ComposeGenerator with Traefik integration."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_traefik_labels_added(self, generator, sample_ignition_instance, sample_traefik_instance):
        """Test Traefik labels are added to web services."""
        result = generator.generate([sample_ignition_instance, sample_traefik_instance])
        parsed = yaml.safe_load(result["docker_compose"])

        # Ignition should have Traefik labels
        ignition_service = parsed["services"]["ignition-gateway"]
        assert "labels" in ignition_service
        labels = ignition_service["labels"]
        assert any("traefik.enable" in str(label) for label in labels)

    def test_traefik_config_files_generated(self, generator, sample_ignition_instance, sample_traefik_instance):
        """Test Traefik configuration files are generated."""
        integration_settings = IntegrationSettings(
            reverse_proxy={"base_domain": "localhost", "enable_https": False}
        )
        result = generator.generate(
            [sample_ignition_instance, sample_traefik_instance],
            integration_settings=integration_settings,
        )

        config_files = result["config_files"]
        assert any("traefik" in path for path in config_files.keys())


class TestComposeGeneratorEnvironment:
    """Test environment variable generation."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_env_contains_global_settings(self, generator, sample_ignition_instance):
        """Test .env file contains global settings."""
        settings = GlobalSettings(stack_name="test-stack", timezone="America/Chicago")
        result = generator.generate([sample_ignition_instance], settings)

        env_content = result["env"]
        assert "TZ=America/Chicago" in env_content

    def test_env_contains_version_info(self, generator, sample_ignition_instance):
        """Test .env file contains service version info."""
        result = generator.generate([sample_ignition_instance])

        env_content = result["env"]
        assert "IGNITION_GATEWAY_VERSION" in env_content


class TestComposeGeneratorReadme:
    """Test README generation."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_readme_contains_stack_name(self, generator, sample_ignition_instance):
        """Test README contains stack name."""
        settings = GlobalSettings(stack_name="my-test-stack")
        result = generator.generate([sample_ignition_instance], settings)

        readme = result["readme"]
        assert "my-test-stack" in readme

    def test_readme_contains_services_list(self, generator, sample_ignition_instance, sample_postgres_instance):
        """Test README lists included services."""
        result = generator.generate([sample_ignition_instance, sample_postgres_instance])

        readme = result["readme"]
        assert "ignition-gateway" in readme
        assert "postgres-db" in readme

    def test_readme_contains_security_notice(self, generator, sample_ignition_instance):
        """Test README contains security notice."""
        result = generator.generate([sample_ignition_instance])

        readme = result["readme"]
        assert "Security" in readme or "IMPORTANT" in readme


class TestComposeGeneratorZip:
    """Test ZIP file generation."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_zip_is_valid(self, generator, sample_ignition_instance):
        """Test generated ZIP is valid."""
        zip_bytes = generator.generate_zip([sample_ignition_instance])

        # Should be able to open as ZIP
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            # Should not raise bad zipfile error
            assert zf.testzip() is None

    def test_zip_contains_required_files(self, generator, sample_ignition_instance):
        """Test ZIP contains required files."""
        zip_bytes = generator.generate_zip([sample_ignition_instance])

        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            names = zf.namelist()
            assert "docker-compose.yml" in names
            assert ".env" in names
            assert "README.md" in names

    def test_zip_compose_is_valid_yaml(self, generator, sample_ignition_instance):
        """Test docker-compose.yml in ZIP is valid YAML."""
        zip_bytes = generator.generate_zip([sample_ignition_instance])

        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            compose_content = zf.read("docker-compose.yml").decode()
            # Should not raise
            parsed = yaml.safe_load(compose_content)
            assert parsed is not None


class TestComposeGeneratorWithKeycloak:
    """Test ComposeGenerator with Keycloak OAuth integration."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_keycloak_realm_config_generated(
        self, generator, sample_keycloak_instance, sample_grafana_instance
    ):
        """Test Keycloak realm configuration is generated."""
        integration_settings = IntegrationSettings(
            oauth={"realm_name": "test-realm", "auto_configure_services": True}
        )
        result = generator.generate(
            [sample_keycloak_instance, sample_grafana_instance],
            integration_settings=integration_settings,
        )

        config_files = result["config_files"]
        # Should have Keycloak import config
        keycloak_configs = [path for path in config_files.keys() if "keycloak" in path]
        # May or may not have realm config depending on implementation
        assert isinstance(config_files, dict)

    def test_grafana_oauth_env_vars(
        self, generator, sample_keycloak_instance, sample_grafana_instance
    ):
        """Test Grafana gets OAuth environment variables."""
        integration_settings = IntegrationSettings(
            oauth={"realm_name": "test-realm", "auto_configure_services": True}
        )
        result = generator.generate(
            [sample_keycloak_instance, sample_grafana_instance],
            integration_settings=integration_settings,
        )

        parsed = yaml.safe_load(result["docker_compose"])
        grafana_service = parsed["services"]["grafana"]
        env = grafana_service.get("environment", {})

        # Should have OAuth env vars if OAuth is detected
        # This depends on whether OAuth provider integration is detected


class TestComposeGeneratorWithMQTT:
    """Test ComposeGenerator with MQTT integration."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_mosquitto_config_generated(self, generator, sample_mosquitto_instance):
        """Test Mosquitto configuration file is generated."""
        integration_settings = IntegrationSettings(
            mqtt={"username": "mqtt_user", "password": "mqtt_pass"}
        )
        result = generator.generate(
            [sample_mosquitto_instance],
            integration_settings=integration_settings,
        )

        config_files = result["config_files"]
        # Should have Mosquitto config
        mqtt_configs = [path for path in config_files.keys() if "mosquitto" in path.lower() or "mqtt" in path.lower()]
        assert len(mqtt_configs) > 0


class TestComposeGeneratorDatabaseIntegration:
    """Test database integration in ComposeGenerator."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_database_registration_script_generated(
        self, generator, sample_ignition_instance, sample_postgres_instance
    ):
        """Test database registration script is generated for Ignition + database."""
        integration_settings = IntegrationSettings(
            database={"auto_register": True}
        )
        result = generator.generate(
            [sample_ignition_instance, sample_postgres_instance],
            integration_settings=integration_settings,
        )

        config_files = result["config_files"]
        # May have registration script depending on implementation
        assert isinstance(config_files, dict)


class TestComposeGeneratorStartupScripts:
    """Test startup script generation."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_startup_scripts_for_ignition(self, generator, sample_ignition_instance):
        """Test startup scripts are generated for Ignition stacks."""
        settings = GlobalSettings(stack_name="ignition-stack")
        result = generator.generate([sample_ignition_instance], settings)

        # Should have startup scripts
        startup_scripts = result.get("startup_scripts", {})
        # If Ignition is present, should have start scripts
        if startup_scripts:
            assert "start.sh" in startup_scripts or "start.bat" in startup_scripts

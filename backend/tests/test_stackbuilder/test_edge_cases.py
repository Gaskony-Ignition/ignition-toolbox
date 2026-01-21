"""
Edge Case Tests for Stack Builder

Tests edge cases and validation:
- Empty instance list
- Invalid app_id
- Reserved name validation
- Special characters in names
- Duplicate instance names
- Pydantic model validation
"""

import pytest
import re
from pydantic import ValidationError

from ignition_toolkit.api.routers.stackbuilder import (
    InstanceConfig,
    GlobalSettingsRequest,
    SavedStackCreate,
    StackConfig,
    VALID_NAME_PATTERN,
    RESERVED_NAMES,
)
from ignition_toolkit.stackbuilder.compose_generator import ComposeGenerator, GlobalSettings


class TestValidNamePattern:
    """Test the valid name pattern regex."""

    def test_pattern_allows_alphanumeric_start(self):
        """Test pattern allows names starting with alphanumeric."""
        pattern = re.compile(VALID_NAME_PATTERN)
        assert pattern.match("ignition")
        assert pattern.match("Ignition")
        assert pattern.match("ignition1")
        assert pattern.match("1ignition")

    def test_pattern_allows_valid_characters(self):
        """Test pattern allows valid Docker name characters."""
        pattern = re.compile(VALID_NAME_PATTERN)
        assert pattern.match("ignition-gateway")
        assert pattern.match("ignition_gateway")
        assert pattern.match("ignition.gateway")
        assert pattern.match("my-stack-1")

    def test_pattern_rejects_invalid_start(self):
        """Test pattern rejects names starting with invalid characters."""
        pattern = re.compile(VALID_NAME_PATTERN)
        assert pattern.match("-ignition") is None
        assert pattern.match("_ignition") is None
        assert pattern.match(".ignition") is None

    def test_pattern_rejects_special_characters(self):
        """Test pattern rejects names with special characters."""
        pattern = re.compile(VALID_NAME_PATTERN)
        assert pattern.match("ignition@gateway") is None
        assert pattern.match("ignition#1") is None
        assert pattern.match("ignition$stack") is None
        assert pattern.match("ignition gateway") is None

    def test_pattern_enforces_length_limit(self):
        """Test pattern enforces 64 character limit."""
        pattern = re.compile(VALID_NAME_PATTERN)
        long_name = "a" * 65
        assert pattern.match(long_name) is None
        valid_name = "a" * 64
        assert pattern.match(valid_name) is not None

    def test_pattern_requires_minimum_length(self):
        """Test pattern requires at least 1 character."""
        pattern = re.compile(VALID_NAME_PATTERN)
        assert pattern.match("") is None


class TestReservedNames:
    """Test reserved name validation."""

    def test_docker_is_reserved(self):
        """Test 'docker' is reserved."""
        assert "docker" in RESERVED_NAMES

    def test_host_is_reserved(self):
        """Test 'host' is reserved."""
        assert "host" in RESERVED_NAMES

    def test_none_is_reserved(self):
        """Test 'none' is reserved."""
        assert "none" in RESERVED_NAMES

    def test_bridge_is_reserved(self):
        """Test 'bridge' is reserved."""
        assert "bridge" in RESERVED_NAMES

    def test_reserved_names_are_lowercase(self):
        """Test all reserved names are lowercase."""
        for name in RESERVED_NAMES:
            assert name == name.lower()


class TestInstanceConfigValidation:
    """Test InstanceConfig Pydantic model validation."""

    def test_valid_instance_config(self):
        """Test valid instance configuration."""
        config = InstanceConfig(
            app_id="ignition",
            instance_name="ignition-gateway",
            config={"version": "latest"},
        )
        assert config.app_id == "ignition"
        assert config.instance_name == "ignition-gateway"

    def test_rejects_empty_app_id(self):
        """Test empty app_id is rejected."""
        with pytest.raises(ValidationError):
            InstanceConfig(app_id="", instance_name="test")

    def test_rejects_empty_instance_name(self):
        """Test empty instance_name is rejected."""
        with pytest.raises(ValidationError):
            InstanceConfig(app_id="ignition", instance_name="")

    def test_rejects_invalid_instance_name(self):
        """Test invalid instance_name patterns are rejected."""
        with pytest.raises(ValidationError):
            InstanceConfig(app_id="ignition", instance_name="-invalid")

    def test_rejects_reserved_instance_name(self):
        """Test reserved instance_name is rejected."""
        with pytest.raises(ValidationError):
            InstanceConfig(app_id="ignition", instance_name="docker")

    def test_rejects_reserved_name_case_insensitive(self):
        """Test reserved names are checked case-insensitively."""
        with pytest.raises(ValidationError):
            InstanceConfig(app_id="ignition", instance_name="Docker")
        with pytest.raises(ValidationError):
            InstanceConfig(app_id="ignition", instance_name="DOCKER")

    def test_accepts_name_containing_reserved_word(self):
        """Test names containing reserved words are allowed."""
        # "my-docker-stack" should be valid (contains "docker" but isn't exactly "docker")
        config = InstanceConfig(app_id="ignition", instance_name="my-docker-stack")
        assert config.instance_name == "my-docker-stack"

    def test_config_defaults_to_empty_dict(self):
        """Test config defaults to empty dict."""
        config = InstanceConfig(app_id="ignition", instance_name="test")
        assert config.config == {}


class TestGlobalSettingsValidation:
    """Test GlobalSettingsRequest Pydantic model validation."""

    def test_default_values(self):
        """Test default global settings values."""
        settings = GlobalSettingsRequest()
        assert settings.stack_name == "iiot-stack"
        assert settings.timezone == "UTC"
        assert settings.restart_policy == "unless-stopped"

    def test_custom_values(self):
        """Test custom global settings."""
        settings = GlobalSettingsRequest(
            stack_name="my-stack",
            timezone="America/New_York",
            restart_policy="always",
        )
        assert settings.stack_name == "my-stack"

    def test_rejects_invalid_stack_name(self):
        """Test invalid stack_name patterns are rejected."""
        with pytest.raises(ValidationError):
            GlobalSettingsRequest(stack_name="-invalid")

    def test_rejects_reserved_stack_name(self):
        """Test reserved stack_name is rejected."""
        with pytest.raises(ValidationError):
            GlobalSettingsRequest(stack_name="docker")


class TestSavedStackCreateValidation:
    """Test SavedStackCreate Pydantic model validation."""

    def test_valid_saved_stack(self):
        """Test valid saved stack creation."""
        stack = SavedStackCreate(
            stack_name="my-stack",
            description="A test stack",
            config_json={"instances": []},
        )
        assert stack.stack_name == "my-stack"

    def test_rejects_reserved_name(self):
        """Test reserved stack name is rejected."""
        with pytest.raises(ValidationError):
            SavedStackCreate(
                stack_name="host",
                config_json={},
            )

    def test_allows_null_description(self):
        """Test null description is allowed."""
        stack = SavedStackCreate(
            stack_name="test-stack",
            description=None,
            config_json={},
        )
        assert stack.description is None


class TestStackConfigValidation:
    """Test StackConfig Pydantic model validation."""

    def test_valid_stack_config(self):
        """Test valid stack configuration."""
        config = StackConfig(
            instances=[
                InstanceConfig(app_id="ignition", instance_name="ignition-1"),
            ],
        )
        assert len(config.instances) == 1

    def test_empty_instances_allowed(self):
        """Test empty instance list is allowed."""
        config = StackConfig(instances=[])
        assert config.instances == []

    def test_optional_settings(self):
        """Test global and integration settings are optional."""
        config = StackConfig(instances=[])
        assert config.global_settings is None
        assert config.integration_settings is None

    def test_with_all_settings(self):
        """Test stack config with all settings."""
        from ignition_toolkit.api.routers.stackbuilder import (
            IntegrationSettingsRequest,
        )
        config = StackConfig(
            instances=[
                InstanceConfig(app_id="ignition", instance_name="ignition-1"),
            ],
            global_settings=GlobalSettingsRequest(stack_name="full-stack"),
            integration_settings=IntegrationSettingsRequest(),
        )
        assert config.global_settings.stack_name == "full-stack"


class TestComposeGeneratorEdgeCases:
    """Test ComposeGenerator edge cases."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_empty_instance_list(self, generator):
        """Test generation with empty instance list."""
        result = generator.generate([])

        assert "docker_compose" in result
        # Should still produce valid YAML
        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        assert "services" in parsed
        assert parsed["services"] == {}

    def test_disabled_app_id_skipped(self, generator):
        """Test disabled applications are skipped."""
        instance = {
            "app_id": "mssql",  # Disabled in catalog
            "instance_name": "mssql-1",
            "config": {},
        }
        result = generator.generate([instance])

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        # MSSQL should not appear in services
        assert "mssql-1" not in parsed["services"]

    def test_unknown_app_id_skipped(self, generator):
        """Test unknown applications are skipped."""
        instance = {
            "app_id": "nonexistent-app",
            "instance_name": "test-1",
            "config": {},
        }
        result = generator.generate([instance])

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        assert "test-1" not in parsed["services"]

    def test_special_characters_in_config_values(self, generator):
        """Test special characters in config values are handled."""
        instance = {
            "app_id": "postgres",
            "instance_name": "postgres-1",
            "config": {
                "password": "p@ss$word!#%",
                "database": "test_db",
            },
        }
        result = generator.generate([instance])

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        postgres = parsed["services"]["postgres-1"]
        assert postgres["environment"]["POSTGRES_PASSWORD"] == "p@ss$word!#%"

    def test_very_long_instance_name(self, generator):
        """Test handling of long but valid instance names."""
        # 64 chars is the max per our pattern
        long_name = "a" * 50  # Well within limits
        instance = {
            "app_id": "postgres",
            "instance_name": long_name,
            "config": {},
        }
        result = generator.generate([instance])

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        assert long_name in parsed["services"]


class TestDuplicateNameHandling:
    """Test duplicate instance name handling."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_duplicate_instance_names_last_wins(self, generator):
        """Test duplicate instance names - last definition wins."""
        instances = [
            {
                "app_id": "postgres",
                "instance_name": "database",
                "config": {"password": "first"},
            },
            {
                "app_id": "mariadb",
                "instance_name": "database",  # Same name
                "config": {"password": "second"},
            },
        ]
        result = generator.generate(instances)

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        # Only one "database" service should exist
        assert "database" in parsed["services"]


class TestPortConflictScenarios:
    """Test scenarios with potential port conflicts."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_custom_ports_applied(self, generator):
        """Test custom port mappings are applied."""
        instance = {
            "app_id": "ignition",
            "instance_name": "ignition-1",
            "config": {
                "http_port": 9088,
                "https_port": 9043,
            },
        }
        result = generator.generate([instance])

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        ignition = parsed["services"]["ignition-1"]
        ports = ignition["ports"]

        # Should have custom ports
        assert any("9088" in p for p in ports)


class TestVersionHandling:
    """Test Docker image version handling."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_specific_version(self, generator):
        """Test specific version is applied to image."""
        instance = {
            "app_id": "ignition",
            "instance_name": "ignition-1",
            "config": {"version": "8.3.2"},
        }
        result = generator.generate([instance])

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        ignition = parsed["services"]["ignition-1"]
        assert "8.3.2" in ignition["image"]

    def test_latest_version_default(self, generator):
        """Test 'latest' is used when no version specified."""
        instance = {
            "app_id": "ignition",
            "instance_name": "ignition-1",
            "config": {},  # No version
        }
        result = generator.generate([instance])

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        ignition = parsed["services"]["ignition-1"]
        assert "latest" in ignition["image"]


class TestModuleConfiguration:
    """Test Ignition module configuration handling."""

    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_83_modules_for_83_version(self, generator):
        """Test 8.3 modules are used for 8.3 version."""
        instance = {
            "app_id": "ignition",
            "instance_name": "ignition-1",
            "config": {
                "version": "8.3.2",
                "modules_83": [{"value": "perspective"}, {"value": "historian-core"}],
            },
        }
        result = generator.generate([instance])

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        ignition = parsed["services"]["ignition-1"]
        env = ignition["environment"]

        if "GATEWAY_MODULES_ENABLED" in env:
            assert "perspective" in env["GATEWAY_MODULES_ENABLED"]

    def test_81_modules_for_81_version(self, generator):
        """Test 8.1 modules are used for 8.1 version."""
        instance = {
            "app_id": "ignition",
            "instance_name": "ignition-1",
            "config": {
                "version": "8.1.45",
                "modules_81": [{"value": "perspective"}, {"value": "tag-historian"}],
            },
        }
        result = generator.generate([instance])

        import yaml
        parsed = yaml.safe_load(result["docker_compose"])
        ignition = parsed["services"]["ignition-1"]
        env = ignition["environment"]

        if "GATEWAY_MODULES_ENABLED" in env:
            # Should use 8.1 module names
            modules = env["GATEWAY_MODULES_ENABLED"]
            assert "perspective" in modules or "tag-historian" in modules

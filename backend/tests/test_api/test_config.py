"""
Tests for configuration API endpoint.

Tests that get_config() returns a properly structured dict with version,
paths, features, server, and websocket_api_key fields.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock


class TestGetConfig:
    """Tests for the /api/config endpoint."""

    def _run_get_config(self, **env_overrides):
        """Helper to run get_config() with optional environment variable overrides."""
        from ignition_toolkit.api.routers.config import get_config

        mock_settings = MagicMock()
        mock_settings.websocket_api_key = "test-ws-key-abc123"

        with patch("ignition_toolkit.api.routers.config.get_settings", return_value=mock_settings):
            if env_overrides:
                with patch.dict("os.environ", env_overrides, clear=False):
                    return asyncio.run(get_config())
            else:
                return asyncio.run(get_config())

    def test_returns_dict(self):
        """get_config() must return a dict."""
        result = self._run_get_config()

        assert isinstance(result, dict)

    def test_top_level_keys_present(self):
        """The response must contain version, paths, features, server, and websocket_api_key."""
        result = self._run_get_config()

        expected_keys = {"version", "paths", "features", "server", "websocket_api_key"}
        missing = expected_keys - set(result.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_paths_contains_required_keys(self):
        """The 'paths' dict must include playbooks_dir, package_root, and user_data_dir."""
        result = self._run_get_config()

        paths = result["paths"]
        assert isinstance(paths, dict)
        expected = {"playbooks_dir", "package_root", "user_data_dir"}
        missing = expected - set(paths.keys())
        assert not missing, f"Missing paths keys: {missing}"

    def test_paths_values_are_strings(self):
        """All path values must be non-empty strings."""
        result = self._run_get_config()

        for key, value in result["paths"].items():
            assert isinstance(value, str), f"paths[{key!r}] must be a string"
            assert value, f"paths[{key!r}] must not be empty"

    def test_features_contains_required_keys(self):
        """The 'features' dict must include ai_enabled, browser_automation, designer_automation."""
        result = self._run_get_config()

        features = result["features"]
        assert isinstance(features, dict)
        expected = {"ai_enabled", "browser_automation", "designer_automation"}
        missing = expected - set(features.keys())
        assert not missing, f"Missing features keys: {missing}"

    def test_features_values_are_booleans(self):
        """All feature flag values must be booleans."""
        result = self._run_get_config()

        for key, value in result["features"].items():
            assert isinstance(value, bool), f"features[{key!r}] must be a bool, got {type(value)}"

    def test_server_contains_required_keys(self):
        """The 'server' dict must include port and host."""
        result = self._run_get_config()

        server = result["server"]
        assert isinstance(server, dict)
        expected = {"port", "host"}
        missing = expected - set(server.keys())
        assert not missing, f"Missing server keys: {missing}"

    def test_server_port_is_integer(self):
        """The server port must be an integer."""
        result = self._run_get_config()

        assert isinstance(result["server"]["port"], int)

    def test_server_host_is_string(self):
        """The server host must be a non-empty string."""
        result = self._run_get_config()

        host = result["server"]["host"]
        assert isinstance(host, str)
        assert host

    def test_websocket_api_key_is_string(self):
        """The websocket_api_key must be a string."""
        result = self._run_get_config()

        key = result["websocket_api_key"]
        assert isinstance(key, str)
        assert key == "test-ws-key-abc123"

    def test_version_comes_from_package_by_default(self):
        """When APP_VERSION env var is not set, version must come from ignition_toolkit.__version__."""
        from ignition_toolkit.api.routers.config import get_config
        import ignition_toolkit

        mock_settings = MagicMock()
        mock_settings.websocket_api_key = "key"

        # Ensure APP_VERSION is absent from the environment
        env_without_app_version = {
            k: v for k, v in __import__("os").environ.items() if k != "APP_VERSION"
        }
        with patch("ignition_toolkit.api.routers.config.get_settings", return_value=mock_settings):
            with patch.dict("os.environ", env_without_app_version, clear=True):
                result = asyncio.run(get_config())

        assert result["version"] == ignition_toolkit.__version__

    def test_app_version_env_var_overrides_version(self):
        """When APP_VERSION env var is set, it must override the package version."""
        result = self._run_get_config(APP_VERSION="99.0.0-test")

        assert result["version"] == "99.0.0-test"

    def test_ai_enabled_false_without_api_key(self):
        """When ANTHROPIC_API_KEY is not set, ai_enabled must be False."""
        from ignition_toolkit.api.routers.config import get_config

        mock_settings = MagicMock()
        mock_settings.websocket_api_key = "key"

        # Strip ANTHROPIC_API_KEY from the environment
        env_without_key = {
            k: v for k, v in __import__("os").environ.items() if k != "ANTHROPIC_API_KEY"
        }
        with patch("ignition_toolkit.api.routers.config.get_settings", return_value=mock_settings):
            with patch.dict("os.environ", env_without_key, clear=True):
                result = asyncio.run(get_config())

        assert result["features"]["ai_enabled"] is False

    def test_ai_enabled_true_with_api_key(self):
        """When ANTHROPIC_API_KEY is set, ai_enabled must be True."""
        result = self._run_get_config(ANTHROPIC_API_KEY="sk-ant-fake-key")

        assert result["features"]["ai_enabled"] is True

    def test_default_server_port(self):
        """The default server port must be 5000 when API_PORT env var is not set."""
        from ignition_toolkit.api.routers.config import get_config

        mock_settings = MagicMock()
        mock_settings.websocket_api_key = "key"

        env_without_port = {
            k: v for k, v in __import__("os").environ.items() if k != "API_PORT"
        }
        with patch("ignition_toolkit.api.routers.config.get_settings", return_value=mock_settings):
            with patch.dict("os.environ", env_without_port, clear=True):
                result = asyncio.run(get_config())

        assert result["server"]["port"] == 5000

    def test_api_port_env_var_overrides_port(self):
        """When API_PORT env var is set, the server port must reflect it."""
        result = self._run_get_config(API_PORT="8080")

        assert result["server"]["port"] == 8080

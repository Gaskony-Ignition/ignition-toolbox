"""
Tests for ignition_toolkit/core/timeouts.py

Covers: TimeoutDefaults values, TimeoutKeys string values, and their completeness.
"""

import pytest


class TestTimeoutDefaults:
    """Tests for the TimeoutDefaults class."""

    def test_class_exists(self):
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults is not None

    def test_gateway_restart_is_positive(self):
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.GATEWAY_RESTART > 0

    def test_module_install_is_positive(self):
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.MODULE_INSTALL > 0

    def test_browser_action_is_positive(self):
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.BROWSER_ACTION > 0

    def test_browser_verify_is_positive(self):
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.BROWSER_VERIFY > 0

    def test_designer_launch_is_positive(self):
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.DESIGNER_LAUNCH > 0

    def test_all_values_are_numeric(self):
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        for attr in ("GATEWAY_RESTART", "MODULE_INSTALL", "BROWSER_ACTION", "BROWSER_VERIFY", "DESIGNER_LAUNCH"):
            value = getattr(TimeoutDefaults, attr)
            assert isinstance(value, (int, float)), f"{attr} must be numeric, got {type(value)}"

    def test_gateway_restart_default_value(self):
        """Gateway restart should default to 120 seconds."""
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.GATEWAY_RESTART == 120

    def test_module_install_default_value(self):
        """Module install should default to 300 seconds."""
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.MODULE_INSTALL == 300

    def test_browser_action_default_value(self):
        """Browser action should default to 30000 ms."""
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.BROWSER_ACTION == 30000

    def test_browser_verify_default_value(self):
        """Browser verify should default to 5000 ms."""
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.BROWSER_VERIFY == 5000

    def test_designer_launch_default_value(self):
        """Designer launch should default to 60 seconds."""
        from ignition_toolkit.core.timeouts import TimeoutDefaults

        assert TimeoutDefaults.DESIGNER_LAUNCH == 60


class TestTimeoutKeys:
    """Tests for the TimeoutKeys class."""

    def test_class_exists(self):
        from ignition_toolkit.core.timeouts import TimeoutKeys

        assert TimeoutKeys is not None

    def test_gateway_restart_is_string(self):
        from ignition_toolkit.core.timeouts import TimeoutKeys

        assert isinstance(TimeoutKeys.GATEWAY_RESTART, str)

    def test_module_install_is_string(self):
        from ignition_toolkit.core.timeouts import TimeoutKeys

        assert isinstance(TimeoutKeys.MODULE_INSTALL, str)

    def test_browser_operation_is_string(self):
        from ignition_toolkit.core.timeouts import TimeoutKeys

        assert isinstance(TimeoutKeys.BROWSER_OPERATION, str)

    def test_designer_launch_is_string(self):
        from ignition_toolkit.core.timeouts import TimeoutKeys

        assert isinstance(TimeoutKeys.DESIGNER_LAUNCH, str)

    def test_key_values_are_lowercase(self):
        """Key strings should be snake_case (lowercase) for consistent dict usage."""
        from ignition_toolkit.core.timeouts import TimeoutKeys

        for attr in ("GATEWAY_RESTART", "MODULE_INSTALL", "BROWSER_OPERATION", "DESIGNER_LAUNCH"):
            value = getattr(TimeoutKeys, attr)
            assert value == value.lower(), f"{attr} key '{value}' should be lowercase"

    def test_gateway_restart_key_value(self):
        from ignition_toolkit.core.timeouts import TimeoutKeys

        assert TimeoutKeys.GATEWAY_RESTART == "gateway_restart"

    def test_module_install_key_value(self):
        from ignition_toolkit.core.timeouts import TimeoutKeys

        assert TimeoutKeys.MODULE_INSTALL == "module_install"

    def test_browser_operation_key_value(self):
        from ignition_toolkit.core.timeouts import TimeoutKeys

        assert TimeoutKeys.BROWSER_OPERATION == "browser_operation"

    def test_designer_launch_key_value(self):
        from ignition_toolkit.core.timeouts import TimeoutKeys

        assert TimeoutKeys.DESIGNER_LAUNCH == "designer_launch"

    def test_all_keys_are_unique(self):
        """No two keys should share the same string value."""
        from ignition_toolkit.core.timeouts import TimeoutKeys

        values = [
            TimeoutKeys.GATEWAY_RESTART,
            TimeoutKeys.MODULE_INSTALL,
            TimeoutKeys.BROWSER_OPERATION,
            TimeoutKeys.DESIGNER_LAUNCH,
        ]
        assert len(values) == len(set(values)), "Duplicate key values found in TimeoutKeys"

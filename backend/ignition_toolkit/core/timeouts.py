"""
Centralized timeout configuration for the Ignition Toolkit.

All timeout defaults and override key strings are defined here.
Import from this module instead of hardcoding magic numbers.

Units:
    - GATEWAY_RESTART: seconds
    - MODULE_INSTALL: seconds
    - BROWSER_ACTION: milliseconds (Playwright API uses ms)
    - BROWSER_VERIFY: milliseconds
    - DESIGNER_LAUNCH: seconds
"""


class TimeoutDefaults:
    """Default timeout values used when no override is provided."""

    GATEWAY_RESTART: int = 120  # seconds
    MODULE_INSTALL: int = 300  # seconds
    BROWSER_ACTION: int = 30000  # milliseconds
    BROWSER_VERIFY: int = 5000  # milliseconds
    DESIGNER_LAUNCH: int = 60  # seconds


class TimeoutKeys:
    """String keys used in the timeout_overrides dictionary passed to playbook execution."""

    GATEWAY_RESTART = "gateway_restart"
    MODULE_INSTALL = "module_install"
    BROWSER_OPERATION = "browser_operation"
    DESIGNER_LAUNCH = "designer_launch"

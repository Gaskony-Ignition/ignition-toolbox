"""
Startup-specific exceptions

Provides clear error messages with recovery instructions for startup failures.
"""

from ignition_toolkit.core.exceptions import ToolkitError


class StartupError(ToolkitError):
    """Base exception for startup failures"""

    def __init__(self, message: str, component: str, recovery_hint: str = ""):
        super().__init__(message, component=component, recovery_hint=recovery_hint)


class EnvironmentError(StartupError):
    """Environment validation failed"""

    def __init__(self, message: str, recovery_hint: str = ""):
        super().__init__(message, component="Environment", recovery_hint=recovery_hint)


class DatabaseInitError(StartupError):
    """Database initialization failed"""

    def __init__(self, message: str, recovery_hint: str = ""):
        super().__init__(
            message,
            component="Database",
            recovery_hint=recovery_hint or "Check database file permissions and disk space",
        )


class VaultInitError(StartupError):
    """Credential vault initialization failed"""

    def __init__(self, message: str, recovery_hint: str = ""):
        super().__init__(
            message,
            component="Vault",
            recovery_hint=recovery_hint or "Run 'ignition-toolkit init' to create vault",
        )

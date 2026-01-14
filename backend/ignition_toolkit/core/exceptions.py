"""
Base exception hierarchy

Provides a consistent exception structure across the toolkit
with clear error messages and recovery hints.
"""


class ToolkitError(Exception):
    """
    Base exception for all toolkit errors

    Attributes:
        message: Error message
        component: Component that raised the error
        recovery_hint: Optional hint for recovery
    """

    def __init__(self, message: str, component: str = "", recovery_hint: str = ""):
        self.component = component
        self.recovery_hint = recovery_hint
        super().__init__(message)

    def __str__(self) -> str:
        msg = super().__str__()
        if self.component:
            msg = f"[{self.component}] {msg}"
        if self.recovery_hint:
            msg += f"\n💡 Recovery: {self.recovery_hint}"
        return msg


class ConfigurationError(ToolkitError):
    """Configuration-related errors"""

    def __init__(self, message: str, recovery_hint: str = ""):
        super().__init__(
            message,
            component="Configuration",
            recovery_hint=recovery_hint or "Check your .env file and settings",
        )


class ValidationError(ToolkitError):
    """Validation errors (parameters, input, etc.)"""

    def __init__(self, message: str, recovery_hint: str = ""):
        super().__init__(message, component="Validation", recovery_hint=recovery_hint)


class AuthenticationError(ToolkitError):
    """Authentication-related errors"""

    def __init__(self, message: str, recovery_hint: str = ""):
        super().__init__(
            message,
            component="Authentication",
            recovery_hint=recovery_hint or "Check your credentials",
        )


class ResourceNotFoundError(ToolkitError):
    """Resource not found errors"""

    def __init__(self, resource: str, identifier: str, recovery_hint: str = ""):
        super().__init__(
            f"{resource} not found: {identifier}",
            component="Resource",
            recovery_hint=recovery_hint,
        )

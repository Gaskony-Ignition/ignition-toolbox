"""
Gateway client exceptions with recovery hints

All exceptions include contextual information and user-friendly recovery hints.
"""


class GatewayException(Exception):  # noqa: N818
    """Base exception for all Gateway-related errors"""

    def __init__(
        self,
        message: str,
        recovery_hint: str = "",
        context: dict | None = None,
    ):
        self.message = message
        self.recovery_hint = recovery_hint
        self.context = context or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format exception message with context and recovery hint"""
        parts = [self.message]
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"[{context_str}]")
        if self.recovery_hint:
            parts.append(f"Hint: {self.recovery_hint}")
        return " ".join(parts)


class AuthenticationError(GatewayException):
    """Raised when authentication fails"""

    def __init__(
        self,
        message: str = "Authentication failed",
        recovery_hint: str = "",
        context: dict | None = None,
    ):
        default_hint = "Verify credentials are correct and not expired. Check username/password in Credentials page."
        super().__init__(
            message,
            recovery_hint or default_hint,
            context,
        )


class ResourceNotFoundError(GatewayException):
    """Raised when a resource (project, module, tag) is not found"""

    def __init__(
        self,
        message: str = "Resource not found",
        recovery_hint: str = "",
        context: dict | None = None,
    ):
        default_hint = "Verify the resource exists on the Gateway. Check project names and paths."
        super().__init__(
            message,
            recovery_hint or default_hint,
            context,
        )


class GatewayConnectionError(GatewayException):
    """Raised when unable to connect to Gateway"""

    def __init__(
        self,
        message: str = "Failed to connect to Gateway",
        recovery_hint: str = "",
        context: dict | None = None,
    ):
        default_hint = "Check Gateway URL is correct and accessible. Verify network connectivity and firewall settings."
        super().__init__(
            message,
            recovery_hint or default_hint,
            context,
        )


class ModuleInstallationError(GatewayException):
    """Raised when module installation fails"""

    def __init__(
        self,
        message: str = "Module installation failed",
        recovery_hint: str = "",
        context: dict | None = None,
    ):
        default_hint = "Verify module file is valid and compatible with Gateway version. Check Gateway logs for details."
        super().__init__(
            message,
            recovery_hint or default_hint,
            context,
        )


class GatewayRestartError(GatewayException):
    """Raised when Gateway restart fails"""

    def __init__(
        self,
        message: str = "Gateway restart failed",
        recovery_hint: str = "",
        context: dict | None = None,
    ):
        default_hint = "Gateway may need manual restart. Check Gateway status page or restart the Ignition service."
        super().__init__(
            message,
            recovery_hint or default_hint,
            context,
        )


class InvalidParameterError(GatewayException):
    """Raised when invalid parameters are provided"""

    def __init__(
        self,
        message: str = "Invalid parameter",
        recovery_hint: str = "",
        context: dict | None = None,
    ):
        default_hint = "Check parameter value and format. Review playbook configuration."
        super().__init__(
            message,
            recovery_hint or default_hint,
            context,
        )

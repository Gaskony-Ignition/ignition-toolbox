"""
Gateway client exceptions
"""


class GatewayException(Exception):
    """Base exception for all Gateway-related errors"""

    pass


class AuthenticationError(GatewayException):
    """Raised when authentication fails"""

    pass


class ResourceNotFoundError(GatewayException):
    """Raised when a resource (project, module, tag) is not found"""

    pass


class GatewayConnectionError(GatewayException):
    """Raised when unable to connect to Gateway"""

    pass


class ModuleInstallationError(GatewayException):
    """Raised when module installation fails"""

    pass


class GatewayRestartError(GatewayException):
    """Raised when Gateway restart fails"""

    pass


class InvalidParameterError(GatewayException):
    """Raised when invalid parameters are provided"""

    pass

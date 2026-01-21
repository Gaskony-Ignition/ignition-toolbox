"""
Custom exceptions for Stack Builder

Provides a hierarchy of exceptions for better error handling and
consistent error responses across the Stack Builder module.
"""


class StackBuilderError(Exception):
    """Base exception for all Stack Builder errors"""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class CatalogError(StackBuilderError):
    """Errors related to the service catalog"""

    pass


class CatalogNotFoundError(CatalogError):
    """Raised when catalog file is not found"""

    pass


class ServiceNotFoundError(CatalogError):
    """Raised when a requested service is not in the catalog"""

    def __init__(self, service_id: str):
        super().__init__(
            f"Service '{service_id}' not found in catalog",
            {"service_id": service_id},
        )


class ServiceDisabledError(CatalogError):
    """Raised when a requested service is disabled"""

    def __init__(self, service_id: str):
        super().__init__(
            f"Service '{service_id}' is disabled in catalog",
            {"service_id": service_id},
        )


class IntegrationError(StackBuilderError):
    """Errors related to integration detection"""

    pass


class IntegrationConflictError(IntegrationError):
    """Raised when conflicting integrations are detected"""

    def __init__(self, conflicts: list[dict]):
        super().__init__(
            "Conflicting integrations detected",
            {"conflicts": conflicts},
        )


class GenerationError(StackBuilderError):
    """Errors during stack generation"""

    pass


class ConfigurationError(GenerationError):
    """Raised when configuration is invalid"""

    def __init__(self, message: str, field: str | None = None):
        details = {"field": field} if field else {}
        super().__init__(message, details)


class ValidationError(StackBuilderError):
    """Errors during input validation"""

    pass


class InvalidNameError(ValidationError):
    """Raised when a name doesn't meet requirements"""

    def __init__(self, name: str, reason: str):
        super().__init__(
            f"Invalid name '{name}': {reason}",
            {"name": name, "reason": reason},
        )


class ReservedNameError(ValidationError):
    """Raised when a reserved name is used"""

    def __init__(self, name: str):
        super().__init__(
            f"Name '{name}' is reserved and cannot be used",
            {"name": name},
        )

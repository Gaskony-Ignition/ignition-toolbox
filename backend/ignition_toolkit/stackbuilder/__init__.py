"""
Stack Builder module for generating Docker Compose stacks

This module provides functionality to:
- Browse a service catalog of IIoT applications
- Configure service instances with custom settings
- Detect integrations between services
- Generate docker-compose.yml and configuration files
"""

from ignition_toolkit.stackbuilder.catalog import ServiceCatalog
from ignition_toolkit.stackbuilder.compose_generator import ComposeGenerator
from ignition_toolkit.stackbuilder.exceptions import (
    CatalogError,
    CatalogNotFoundError,
    ConfigurationError,
    GenerationError,
    IntegrationConflictError,
    IntegrationError,
    InvalidNameError,
    ReservedNameError,
    ServiceDisabledError,
    ServiceNotFoundError,
    StackBuilderError,
    ValidationError,
)
from ignition_toolkit.stackbuilder.integration_engine import IntegrationEngine

__all__ = [
    # Core classes
    "ServiceCatalog",
    "IntegrationEngine",
    "ComposeGenerator",
    # Exceptions
    "StackBuilderError",
    "CatalogError",
    "CatalogNotFoundError",
    "ServiceNotFoundError",
    "ServiceDisabledError",
    "IntegrationError",
    "IntegrationConflictError",
    "GenerationError",
    "ConfigurationError",
    "ValidationError",
    "InvalidNameError",
    "ReservedNameError",
]

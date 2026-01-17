"""
Stack Builder module for generating Docker Compose stacks

This module provides functionality to:
- Browse a service catalog of IIoT applications
- Configure service instances with custom settings
- Detect integrations between services
- Generate docker-compose.yml and configuration files
"""

from ignition_toolkit.stackbuilder.catalog import ServiceCatalog
from ignition_toolkit.stackbuilder.integration_engine import IntegrationEngine

__all__ = ["ServiceCatalog", "IntegrationEngine"]

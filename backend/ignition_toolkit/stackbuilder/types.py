"""
Type definitions for Stack Builder

Provides TypedDict definitions for better type hints and IDE support.
"""

from typing import Any, TypedDict


class InstanceConfig(TypedDict):
    """Configuration for a service instance"""

    app_id: str
    instance_name: str
    config: dict[str, Any]


class ServiceConfig(TypedDict, total=False):
    """Docker Compose service configuration"""

    image: str
    container_name: str
    environment: dict[str, str]
    ports: list[str]
    volumes: list[str]
    networks: list[str]
    depends_on: list[str] | dict[str, dict[str, str]]
    restart: str
    labels: list[str]
    command: str
    healthcheck: dict[str, Any]
    cap_add: list[str]


class IntegrationResult(TypedDict):
    """Result from integration detection"""

    integrations: dict[str, Any]
    conflicts: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    auto_add_services: list[dict[str, Any]]


class GenerationResult(TypedDict):
    """Result from stack generation"""

    docker_compose: str
    env_file: str
    readme: str
    config_files: dict[str, str]


class ReverseProxySettings(TypedDict, total=False):
    """Reverse proxy integration settings"""

    base_domain: str
    enable_https: bool
    letsencrypt_email: str


class MqttSettings(TypedDict, total=False):
    """MQTT integration settings"""

    enable_tls: bool
    username: str
    password: str
    tls_port: int


class OAuthSettings(TypedDict, total=False):
    """OAuth integration settings"""

    realm_name: str
    auto_configure_services: bool


class DatabaseSettings(TypedDict, total=False):
    """Database integration settings"""

    auto_register: bool


class EmailSettings(TypedDict, total=False):
    """Email integration settings"""

    from_address: str
    auto_configure_services: bool

"""
Configuration file generators for Stack Builder

Generates config files for MQTT, Grafana datasources, Traefik, etc.
"""

import base64
import hashlib
import os
import secrets
from typing import Any

import yaml


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password.

    Args:
        length: Desired password length (default 16)

    Returns:
        URL-safe random string suitable for passwords
    """
    return secrets.token_urlsafe(length)[:length]


def generate_secure_secret(length: int = 32) -> str:
    """
    Generate a cryptographically secure random secret.

    Args:
        length: Desired secret length (default 32)

    Returns:
        URL-safe random string suitable for OAuth secrets, API keys, etc.
    """
    return secrets.token_urlsafe(length)


def generate_mosquitto_password_file(username: str, password: str) -> str:
    """
    Generate Mosquitto password file content with proper PBKDF2-SHA512 hashing.

    Uses the Mosquitto 2.0+ password format: $7$<base64(salt+derived_key)>

    Args:
        username: MQTT username
        password: MQTT password (will be hashed)

    Returns:
        Password file content with hashed password
    """
    # Mosquitto 2.0+ PBKDF2-SHA512 format
    # $7$ prefix indicates PBKDF2-SHA512
    salt = os.urandom(12)
    iterations = 101  # Mosquitto default
    dk = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, iterations, dklen=64)
    hash_b64 = base64.b64encode(salt + dk).decode()
    return f"{username}:$7${hash_b64}\n"


def generate_prometheus_config() -> str:
    """
    Generate minimal Prometheus configuration file.

    Returns:
        YAML configuration string for Prometheus with default scrape config
    """
    return """global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
"""


def generate_mosquitto_config(
    username: str = "",
    password: str = "",
    enable_tls: bool = False,
    tls_port: int = 8883,
) -> str:
    """
    Generate Mosquitto MQTT broker configuration file.

    Args:
        username: MQTT username for authentication (empty for anonymous)
        password: MQTT password for authentication (empty for anonymous)
        enable_tls: Whether to enable TLS listener
        tls_port: Port for TLS listener (default 8883)

    Returns:
        Mosquitto configuration file content
    """
    config = []

    # Listener configuration
    config.append("listener 1883")
    config.append("protocol mqtt")
    config.append("")

    if enable_tls:
        config.append(f"listener {tls_port}")
        config.append("protocol mqtt")
        config.append("# TLS configuration - add certificate paths here")
        config.append("# cafile /mosquitto/config/ca.crt")
        config.append("# certfile /mosquitto/config/server.crt")
        config.append("# keyfile /mosquitto/config/server.key")
        config.append("")

    # Authentication
    if username and password:
        config.append("allow_anonymous false")
        config.append("password_file /mosquitto/config/passwd")
    else:
        config.append("allow_anonymous true")

    config.append("")
    config.append("# Persistence")
    config.append("persistence true")
    config.append("persistence_location /mosquitto/data/")
    config.append("")
    config.append("# Logging")
    config.append("log_dest file /mosquitto/log/mosquitto.log")
    config.append("log_dest stdout")
    config.append("log_type all")

    return "\n".join(config)


def generate_emqx_config(
    username: str = "", password: str = "", enable_tls: bool = False
) -> str:
    """
    Generate EMQX MQTT broker configuration snippet.

    Args:
        username: MQTT username for authentication
        password: MQTT password for authentication
        enable_tls: Whether TLS is enabled (currently unused)

    Returns:
        YAML configuration string for EMQX authentication
    """
    config: dict[str, Any] = {"authentication": []}

    if username and password:
        config["authentication"].append({
            "mechanism": "password_based",
            "backend": "built_in_database",
            "user_id_type": "username",
        })

    return yaml.dump(config, default_flow_style=False)


def generate_grafana_datasources(datasources: list[dict[str, Any]]) -> str:
    """
    Generate Grafana datasource provisioning configuration.

    Args:
        datasources: List of datasource configurations with format:
            [
                {"type": "prometheus", "instance_name": "prometheus", "config": {}},
                {"type": "postgres", "instance_name": "postgres-1", "config": {...}},
            ]

    Returns:
        YAML provisioning configuration for Grafana datasources
    """
    provisioning: dict[str, Any] = {"apiVersion": 1, "datasources": []}

    for idx, ds in enumerate(datasources):
        ds_type = ds.get("type")
        instance_name = ds.get("instance_name")
        config = ds.get("config", {})

        if ds_type == "prometheus":
            provisioning["datasources"].append({
                "name": "Prometheus",
                "type": "prometheus",
                "access": "proxy",
                "url": f"http://{instance_name}:9090",
                "isDefault": idx == 0,
                "editable": True,
            })

        elif ds_type == "postgres":
            db_name = config.get("database", "postgres")
            db_user = config.get("username", "postgres")
            db_password = config.get("password", "postgres")
            port = config.get("port", 5432)

            provisioning["datasources"].append({
                "name": f"PostgreSQL-{instance_name}",
                "type": "postgres",
                "access": "proxy",
                "url": f"{instance_name}:{port}",
                "database": db_name,
                "user": db_user,
                "secureJsonData": {"password": db_password},
                "jsonData": {"sslmode": "disable", "postgresVersion": 1400},
                "editable": True,
            })

        elif ds_type in ("mysql", "mariadb"):
            db_name = config.get("database", "mysql")
            db_user = config.get("username", "root")
            db_password = config.get("password", "password")
            port = config.get("port", 3306)

            provisioning["datasources"].append({
                "name": f"MySQL-{instance_name}",
                "type": "mysql",
                "access": "proxy",
                "url": f"{instance_name}:{port}",
                "database": db_name,
                "user": db_user,
                "secureJsonData": {"password": db_password},
                "editable": True,
            })

    return yaml.dump(provisioning, default_flow_style=False, sort_keys=False)


def generate_traefik_static_config(
    enable_https: bool = False,
    letsencrypt_email: str = "",
    network_name: str = "iiot-stack-network",
) -> str:
    """
    Generate Traefik static configuration (traefik.yml).

    Args:
        enable_https: Whether to enable HTTPS entrypoint
        letsencrypt_email: Email for Let's Encrypt certificate generation
        network_name: Docker network name for Traefik to monitor

    Returns:
        YAML configuration string for Traefik
    """
    # Dashboard is enabled but secured (requires auth middleware)
    # For development, access via: traefik:8080 from within Docker network
    # For production, configure basicAuth or forwardAuth middleware
    config: dict[str, Any] = {
        "api": {"dashboard": True, "insecure": False},
        "entryPoints": {
            "web": {"address": ":80"},
            "traefik": {"address": ":8080"},  # Dashboard entrypoint
        },
        "providers": {
            "docker": {"exposedByDefault": False, "network": network_name},
            "file": {"directory": "/etc/traefik/dynamic", "watch": True},
        },
        "log": {"level": "INFO"},
    }

    if enable_https:
        config["entryPoints"]["websecure"] = {"address": ":443"}

        if letsencrypt_email:
            config["certificatesResolvers"] = {
                "letsencrypt": {
                    "acme": {
                        "email": letsencrypt_email,
                        "storage": "/letsencrypt/acme.json",
                        "httpChallenge": {"entryPoint": "web"},
                    }
                }
            }

    return yaml.dump(config, default_flow_style=False, sort_keys=False)


def generate_traefik_dynamic_config(
    services: list[dict[str, Any]],
    domain: str = "localhost",
    enable_https: bool = False,
) -> str:
    """
    Generate Traefik dynamic configuration for services.

    Creates routers and load balancer configuration for each service.

    Args:
        services: List of service configurations with format:
            [
                {"instance_name": "ignition-1", "subdomain": "ignition", "port": 8088},
                {"instance_name": "grafana", "subdomain": "grafana", "port": 3000}
            ]
        domain: Base domain for service routing (default "localhost")
        enable_https: Whether to use websecure entrypoint with TLS

    Returns:
        YAML configuration string for Traefik dynamic routing
    """
    config: dict[str, Any] = {"http": {"routers": {}, "services": {}}}

    for svc in services:
        instance_name = svc["instance_name"]
        subdomain = svc.get("subdomain", instance_name)
        port = svc["port"]

        # Router configuration
        router_name = f"{instance_name}-router"
        config["http"]["routers"][router_name] = {
            "rule": f"Host(`{subdomain}.{domain}`)",
            "service": instance_name,
            "entryPoints": ["websecure" if enable_https else "web"],
        }

        if enable_https:
            config["http"]["routers"][router_name]["tls"] = {
                "certResolver": "letsencrypt"
            }

        # Service configuration
        config["http"]["services"][instance_name] = {
            "loadBalancer": {"servers": [{"url": f"http://{instance_name}:{port}"}]}
        }

    return yaml.dump(config, default_flow_style=False, sort_keys=False)


def generate_oauth_env_vars(
    service_id: str,
    provider: str,
    realm_name: str = "iiot",
    base_domain: str = "localhost",
    client_secret: str | None = None,
) -> dict[str, str]:
    """
    Generate OAuth environment variables for a service.

    Args:
        service_id: The service ID (e.g., "grafana", "n8n")
        provider: The OAuth provider hostname (e.g., "keycloak")
        realm_name: Keycloak realm name
        base_domain: Base domain for callbacks
        client_secret: OAuth client secret (generated if not provided)

    Returns:
        Dictionary of environment variables for OAuth configuration
    """
    env_vars: dict[str, str] = {}

    keycloak_base = f"http://{provider}:8080/realms/{realm_name}/protocol/openid-connect"

    if not client_secret:
        # Generate a secure random secret if not provided
        client_secret = generate_secure_secret(32)

    if service_id == "grafana":
        env_vars.update({
            "GF_AUTH_GENERIC_OAUTH_ENABLED": "true",
            "GF_AUTH_GENERIC_OAUTH_NAME": "Keycloak",
            "GF_AUTH_GENERIC_OAUTH_CLIENT_ID": "grafana",
            "GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET": client_secret,
            "GF_AUTH_GENERIC_OAUTH_SCOPES": "openid profile email",
            "GF_AUTH_GENERIC_OAUTH_AUTH_URL": f"{keycloak_base}/auth",
            "GF_AUTH_GENERIC_OAUTH_TOKEN_URL": f"{keycloak_base}/token",
            "GF_AUTH_GENERIC_OAUTH_API_URL": f"{keycloak_base}/userinfo",
            "GF_AUTH_GENERIC_OAUTH_ALLOW_SIGN_UP": "true",
        })

    elif service_id == "n8n":
        env_vars.update({
            "N8N_OAUTH_ENABLED": "true",
            "N8N_OAUTH_CLIENT_ID": "n8n",
            "N8N_OAUTH_CLIENT_SECRET": client_secret,
            "N8N_OAUTH_AUTH_URL": f"{keycloak_base}/auth",
            "N8N_OAUTH_TOKEN_URL": f"{keycloak_base}/token",
        })

    return env_vars


def generate_email_env_vars(
    service_id: str,
    mailhog_instance: str = "mailhog",
    from_address: str = "noreply@iiot.local",
) -> dict[str, str]:
    """
    Generate email/SMTP environment variables for services.

    Configures services to send email through MailHog for testing.

    Args:
        service_id: The service ID (e.g., "grafana", "ignition", "n8n", "keycloak")
        mailhog_instance: MailHog container name (default "mailhog")
        from_address: Email address to use as sender (default "noreply@iiot.local")

    Returns:
        Dictionary of environment variables for SMTP configuration
    """
    env_vars: dict[str, str] = {}

    if service_id == "grafana":
        env_vars.update({
            "GF_SMTP_ENABLED": "true",
            "GF_SMTP_HOST": f"{mailhog_instance}:1025",
            "GF_SMTP_FROM_ADDRESS": from_address,
            "GF_SMTP_FROM_NAME": "Grafana",
            "GF_SMTP_SKIP_VERIFY": "true",
        })

    elif service_id == "ignition":
        env_vars.update({
            "GATEWAY_SMTP_HOST": mailhog_instance,
            "GATEWAY_SMTP_PORT": "1025",
            "GATEWAY_SMTP_FROM": from_address,
        })

    elif service_id == "n8n":
        env_vars.update({
            "N8N_EMAIL_MODE": "smtp",
            "N8N_SMTP_HOST": mailhog_instance,
            "N8N_SMTP_PORT": "1025",
            "N8N_SMTP_SENDER": from_address,
        })

    elif service_id == "keycloak":
        env_vars.update({
            "KC_SMTP_HOST": mailhog_instance,
            "KC_SMTP_PORT": "1025",
            "KC_SMTP_FROM": from_address,
        })

    return env_vars

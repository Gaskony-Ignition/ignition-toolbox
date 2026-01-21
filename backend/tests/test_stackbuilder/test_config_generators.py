"""
Unit Tests for Config Generators

Tests the config_generators.py module functionality:
- Mosquitto configuration generation
- Grafana datasource provisioning
- Traefik static and dynamic configuration
- OAuth environment variable generation
- Email/SMTP environment variable generation
- Password and secret generation
"""

import pytest
import yaml

from ignition_toolkit.stackbuilder.config_generators import (
    generate_secure_password,
    generate_secure_secret,
    generate_mosquitto_config,
    generate_mosquitto_password_file,
    generate_prometheus_config,
    generate_emqx_config,
    generate_grafana_datasources,
    generate_traefik_static_config,
    generate_traefik_dynamic_config,
    generate_oauth_env_vars,
    generate_email_env_vars,
)


class TestSecurePasswordGeneration:
    """Test secure password generation."""

    def test_default_password_length(self):
        """Test default password length is 16."""
        password = generate_secure_password()
        assert len(password) == 16

    def test_custom_password_length(self):
        """Test custom password length."""
        password = generate_secure_password(length=32)
        assert len(password) == 32

    def test_passwords_are_unique(self):
        """Test generated passwords are unique."""
        passwords = [generate_secure_password() for _ in range(100)]
        # All should be unique
        assert len(set(passwords)) == 100

    def test_password_contains_safe_characters(self):
        """Test password contains only URL-safe characters."""
        password = generate_secure_password(length=64)
        # URL-safe base64 characters
        safe_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in safe_chars for c in password)


class TestSecureSecretGeneration:
    """Test secure secret generation."""

    def test_default_secret_length(self):
        """Test default secret length is at least 32."""
        secret = generate_secure_secret()
        assert len(secret) >= 32

    def test_custom_secret_length(self):
        """Test custom secret length."""
        secret = generate_secure_secret(length=64)
        # URL-safe encoding may produce slightly longer output
        assert len(secret) >= 64

    def test_secrets_are_unique(self):
        """Test generated secrets are unique."""
        secrets = [generate_secure_secret() for _ in range(100)]
        assert len(set(secrets)) == 100


class TestMosquittoConfigGeneration:
    """Test Mosquitto configuration generation."""

    def test_basic_config_no_auth(self):
        """Test basic Mosquitto config without authentication."""
        config = generate_mosquitto_config()
        assert "listener 1883" in config
        assert "allow_anonymous true" in config
        assert "persistence true" in config

    def test_config_with_auth(self):
        """Test Mosquitto config with authentication."""
        config = generate_mosquitto_config(username="mqtt_user", password="mqtt_pass")
        assert "allow_anonymous false" in config
        assert "password_file /mosquitto/config/passwd" in config

    def test_config_with_tls(self):
        """Test Mosquitto config with TLS enabled."""
        config = generate_mosquitto_config(enable_tls=True, tls_port=8883)
        assert "listener 8883" in config
        # Should have TLS configuration comments
        assert "TLS configuration" in config or "certfile" in config

    def test_config_with_custom_tls_port(self):
        """Test Mosquitto config with custom TLS port."""
        config = generate_mosquitto_config(enable_tls=True, tls_port=9883)
        assert "listener 9883" in config


class TestMosquittoPasswordFileGeneration:
    """Test Mosquitto password file generation."""

    def test_password_file_format(self):
        """Test password file has correct format."""
        content = generate_mosquitto_password_file("testuser", "testpass")
        assert content.startswith("testuser:")
        # Should have PBKDF2-SHA512 hash prefix
        assert "$7$" in content

    def test_password_file_hashes_password(self):
        """Test password is hashed, not plaintext."""
        content = generate_mosquitto_password_file("user", "plainpassword")
        # Plaintext password should not appear
        assert "plainpassword" not in content
        # But username should be present
        assert "user:" in content

    def test_different_passwords_different_hashes(self):
        """Test different passwords produce different hashes."""
        content1 = generate_mosquitto_password_file("user", "password1")
        content2 = generate_mosquitto_password_file("user", "password2")
        # Hashes should be different
        assert content1 != content2


class TestPrometheusConfigGeneration:
    """Test Prometheus configuration generation."""

    def test_prometheus_config_is_valid_yaml(self):
        """Test Prometheus config is valid YAML."""
        config = generate_prometheus_config()
        parsed = yaml.safe_load(config)
        assert parsed is not None

    def test_prometheus_config_has_global(self):
        """Test Prometheus config has global section."""
        config = generate_prometheus_config()
        parsed = yaml.safe_load(config)
        assert "global" in parsed
        assert "scrape_interval" in parsed["global"]

    def test_prometheus_config_has_scrape_configs(self):
        """Test Prometheus config has scrape_configs."""
        config = generate_prometheus_config()
        parsed = yaml.safe_load(config)
        assert "scrape_configs" in parsed


class TestEmqxConfigGeneration:
    """Test EMQX configuration generation."""

    def test_emqx_config_without_auth(self):
        """Test EMQX config without authentication."""
        config = generate_emqx_config()
        parsed = yaml.safe_load(config)
        assert "authentication" in parsed

    def test_emqx_config_with_auth(self):
        """Test EMQX config with authentication."""
        config = generate_emqx_config(username="emqx_user", password="emqx_pass")
        parsed = yaml.safe_load(config)
        assert "authentication" in parsed
        # Should have authentication mechanism
        auth = parsed["authentication"]
        assert len(auth) > 0


class TestGrafanaDatasourceGeneration:
    """Test Grafana datasource provisioning generation."""

    def test_empty_datasources(self):
        """Test generation with empty datasource list."""
        config = generate_grafana_datasources([])
        parsed = yaml.safe_load(config)
        assert parsed["apiVersion"] == 1
        assert parsed["datasources"] == []

    def test_prometheus_datasource(self):
        """Test Prometheus datasource generation."""
        datasources = [
            {"type": "prometheus", "instance_name": "prometheus", "config": {}}
        ]
        config = generate_grafana_datasources(datasources)
        parsed = yaml.safe_load(config)

        assert len(parsed["datasources"]) == 1
        ds = parsed["datasources"][0]
        assert ds["type"] == "prometheus"
        assert ds["name"] == "Prometheus"
        assert "http://prometheus:9090" in ds["url"]

    def test_postgres_datasource(self):
        """Test PostgreSQL datasource generation."""
        datasources = [
            {
                "type": "postgres",
                "instance_name": "postgres-db",
                "config": {
                    "database": "mydb",
                    "username": "dbuser",
                    "password": "dbpass",
                    "port": 5432,
                }
            }
        ]
        config = generate_grafana_datasources(datasources)
        parsed = yaml.safe_load(config)

        assert len(parsed["datasources"]) == 1
        ds = parsed["datasources"][0]
        assert ds["type"] == "postgres"
        assert ds["database"] == "mydb"
        assert ds["user"] == "dbuser"

    def test_mysql_datasource(self):
        """Test MySQL/MariaDB datasource generation."""
        datasources = [
            {
                "type": "mariadb",
                "instance_name": "mariadb-1",
                "config": {
                    "database": "mydb",
                    "username": "root",
                    "password": "rootpass",
                }
            }
        ]
        config = generate_grafana_datasources(datasources)
        parsed = yaml.safe_load(config)

        assert len(parsed["datasources"]) == 1
        ds = parsed["datasources"][0]
        assert ds["type"] == "mysql"

    def test_multiple_datasources(self):
        """Test multiple datasource generation."""
        datasources = [
            {"type": "prometheus", "instance_name": "prometheus", "config": {}},
            {"type": "postgres", "instance_name": "postgres-db", "config": {}},
        ]
        config = generate_grafana_datasources(datasources)
        parsed = yaml.safe_load(config)

        assert len(parsed["datasources"]) == 2
        # First datasource should be default
        assert parsed["datasources"][0]["isDefault"] is True

    def test_datasource_config_is_valid_yaml(self):
        """Test generated config is valid YAML."""
        datasources = [
            {"type": "prometheus", "instance_name": "prometheus", "config": {}}
        ]
        config = generate_grafana_datasources(datasources)
        # Should not raise
        parsed = yaml.safe_load(config)
        assert parsed is not None


class TestTraefikStaticConfigGeneration:
    """Test Traefik static configuration generation."""

    def test_basic_http_config(self):
        """Test basic HTTP-only Traefik config."""
        config = generate_traefik_static_config()
        parsed = yaml.safe_load(config)

        assert "api" in parsed
        assert "entryPoints" in parsed
        assert "web" in parsed["entryPoints"]
        assert parsed["entryPoints"]["web"]["address"] == ":80"

    def test_https_config(self):
        """Test Traefik config with HTTPS enabled."""
        config = generate_traefik_static_config(enable_https=True)
        parsed = yaml.safe_load(config)

        assert "websecure" in parsed["entryPoints"]
        assert parsed["entryPoints"]["websecure"]["address"] == ":443"

    def test_letsencrypt_config(self):
        """Test Traefik config with Let's Encrypt."""
        config = generate_traefik_static_config(
            enable_https=True,
            letsencrypt_email="admin@example.com"
        )
        parsed = yaml.safe_load(config)

        assert "certificatesResolvers" in parsed
        assert "letsencrypt" in parsed["certificatesResolvers"]
        acme = parsed["certificatesResolvers"]["letsencrypt"]["acme"]
        assert acme["email"] == "admin@example.com"

    def test_providers_config(self):
        """Test Traefik has Docker and file providers."""
        config = generate_traefik_static_config()
        parsed = yaml.safe_load(config)

        assert "providers" in parsed
        assert "docker" in parsed["providers"]
        assert "file" in parsed["providers"]


class TestTraefikDynamicConfigGeneration:
    """Test Traefik dynamic configuration generation."""

    def test_empty_services(self):
        """Test generation with empty service list."""
        config = generate_traefik_dynamic_config([])
        parsed = yaml.safe_load(config)

        assert "http" in parsed
        assert "routers" in parsed["http"]
        assert "services" in parsed["http"]

    def test_single_service_http(self):
        """Test single service HTTP configuration."""
        services = [
            {"instance_name": "ignition-1", "subdomain": "ignition", "port": 8088}
        ]
        config = generate_traefik_dynamic_config(services, domain="localhost")
        parsed = yaml.safe_load(config)

        routers = parsed["http"]["routers"]
        assert "ignition-1-router" in routers
        router = routers["ignition-1-router"]
        assert "Host(`ignition.localhost`)" in router["rule"]
        assert "web" in router["entryPoints"]

    def test_single_service_https(self):
        """Test single service HTTPS configuration."""
        services = [
            {"instance_name": "grafana", "subdomain": "grafana", "port": 3000}
        ]
        config = generate_traefik_dynamic_config(
            services,
            domain="example.com",
            enable_https=True
        )
        parsed = yaml.safe_load(config)

        router = parsed["http"]["routers"]["grafana-router"]
        assert "websecure" in router["entryPoints"]
        assert "tls" in router

    def test_multiple_services(self):
        """Test multiple services configuration."""
        services = [
            {"instance_name": "ignition-1", "subdomain": "ignition", "port": 8088},
            {"instance_name": "grafana", "subdomain": "grafana", "port": 3000},
            {"instance_name": "keycloak", "subdomain": "auth", "port": 8180},
        ]
        config = generate_traefik_dynamic_config(services, domain="iiot.local")
        parsed = yaml.safe_load(config)

        routers = parsed["http"]["routers"]
        assert len(routers) == 3

        services_section = parsed["http"]["services"]
        assert len(services_section) == 3


class TestOAuthEnvVarGeneration:
    """Test OAuth environment variable generation."""

    def test_grafana_oauth_env_vars(self):
        """Test Grafana OAuth environment variables."""
        env_vars = generate_oauth_env_vars(
            service_id="grafana",
            provider="keycloak",
            realm_name="iiot",
            client_secret="test-secret"
        )

        assert "GF_AUTH_GENERIC_OAUTH_ENABLED" in env_vars
        assert env_vars["GF_AUTH_GENERIC_OAUTH_ENABLED"] == "true"
        assert "GF_AUTH_GENERIC_OAUTH_CLIENT_ID" in env_vars
        assert env_vars["GF_AUTH_GENERIC_OAUTH_CLIENT_ID"] == "grafana"
        assert "GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET" in env_vars
        assert env_vars["GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET"] == "test-secret"

    def test_n8n_oauth_env_vars(self):
        """Test n8n OAuth environment variables."""
        env_vars = generate_oauth_env_vars(
            service_id="n8n",
            provider="keycloak",
            realm_name="iiot",
            client_secret="n8n-secret"
        )

        assert "N8N_OAUTH_ENABLED" in env_vars
        assert "N8N_OAUTH_CLIENT_ID" in env_vars
        assert env_vars["N8N_OAUTH_CLIENT_ID"] == "n8n"

    def test_oauth_generates_secret_if_not_provided(self):
        """Test OAuth generates secret if not provided."""
        env_vars = generate_oauth_env_vars(
            service_id="grafana",
            provider="keycloak",
            realm_name="iiot"
        )

        # Should have a generated secret
        assert "GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET" in env_vars
        secret = env_vars["GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET"]
        assert len(secret) > 0

    def test_oauth_urls_include_realm(self):
        """Test OAuth URLs include realm name."""
        env_vars = generate_oauth_env_vars(
            service_id="grafana",
            provider="keycloak",
            realm_name="custom-realm"
        )

        auth_url = env_vars.get("GF_AUTH_GENERIC_OAUTH_AUTH_URL", "")
        assert "custom-realm" in auth_url

    def test_unknown_service_returns_empty(self):
        """Test unknown service returns empty dict."""
        env_vars = generate_oauth_env_vars(
            service_id="unknown-service",
            provider="keycloak",
            realm_name="iiot"
        )

        assert env_vars == {}


class TestEmailEnvVarGeneration:
    """Test email/SMTP environment variable generation."""

    def test_grafana_email_env_vars(self):
        """Test Grafana SMTP environment variables."""
        env_vars = generate_email_env_vars(
            service_id="grafana",
            mailhog_instance="mailhog",
            from_address="grafana@example.com"
        )

        assert "GF_SMTP_ENABLED" in env_vars
        assert env_vars["GF_SMTP_ENABLED"] == "true"
        assert "GF_SMTP_HOST" in env_vars
        assert "mailhog:1025" in env_vars["GF_SMTP_HOST"]
        assert env_vars["GF_SMTP_FROM_ADDRESS"] == "grafana@example.com"

    def test_ignition_email_env_vars(self):
        """Test Ignition SMTP environment variables."""
        env_vars = generate_email_env_vars(
            service_id="ignition",
            mailhog_instance="mailhog",
            from_address="ignition@example.com"
        )

        assert "GATEWAY_SMTP_HOST" in env_vars
        assert env_vars["GATEWAY_SMTP_HOST"] == "mailhog"
        assert "GATEWAY_SMTP_PORT" in env_vars
        assert env_vars["GATEWAY_SMTP_PORT"] == "1025"

    def test_n8n_email_env_vars(self):
        """Test n8n SMTP environment variables."""
        env_vars = generate_email_env_vars(
            service_id="n8n",
            mailhog_instance="mailhog"
        )

        assert "N8N_EMAIL_MODE" in env_vars
        assert env_vars["N8N_EMAIL_MODE"] == "smtp"
        assert "N8N_SMTP_HOST" in env_vars

    def test_keycloak_email_env_vars(self):
        """Test Keycloak SMTP environment variables."""
        env_vars = generate_email_env_vars(
            service_id="keycloak",
            mailhog_instance="mail-test"
        )

        assert "KC_SMTP_HOST" in env_vars
        assert env_vars["KC_SMTP_HOST"] == "mail-test"
        assert "KC_SMTP_PORT" in env_vars

    def test_unknown_service_returns_empty(self):
        """Test unknown service returns empty dict."""
        env_vars = generate_email_env_vars(
            service_id="unknown-service",
            mailhog_instance="mailhog"
        )

        assert env_vars == {}

    def test_custom_mailhog_instance(self):
        """Test custom MailHog instance name."""
        env_vars = generate_email_env_vars(
            service_id="grafana",
            mailhog_instance="custom-mailhog"
        )

        assert "custom-mailhog" in env_vars["GF_SMTP_HOST"]

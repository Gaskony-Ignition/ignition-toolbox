"""
Unit Tests for Keycloak Realm Generator

Tests the keycloak_generator.py module functionality:
- Client secret generation
- Realm configuration generation
- User import configuration
- Client configuration for various services
- README section generation
"""

import pytest
import json

from ignition_toolkit.stackbuilder.keycloak_generator import (
    generate_client_secret,
    generate_keycloak_realm,
    generate_keycloak_readme_section,
)


class TestClientSecretGeneration:
    """Test client secret generation."""

    def test_secret_is_string(self):
        """Test generated secret is a string."""
        secret = generate_client_secret()
        assert isinstance(secret, str)

    def test_secret_is_long_enough(self):
        """Test generated secret is sufficiently long."""
        secret = generate_client_secret()
        # URL-safe base64 encoding of 32 bytes should be ~43 chars
        assert len(secret) >= 32

    def test_secrets_are_unique(self):
        """Test generated secrets are unique."""
        secrets = [generate_client_secret() for _ in range(100)]
        assert len(set(secrets)) == 100

    def test_secret_is_url_safe(self):
        """Test generated secret is URL-safe."""
        secret = generate_client_secret()
        # URL-safe base64 characters
        safe_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in safe_chars for c in secret)


class TestRealmBasicGeneration:
    """Test basic Keycloak realm generation."""

    def test_realm_has_required_fields(self):
        """Test generated realm has all required fields."""
        realm = generate_keycloak_realm()

        assert "id" in realm
        assert "realm" in realm
        assert "displayName" in realm
        assert "enabled" in realm
        assert "roles" in realm
        assert "clientScopes" in realm
        assert "users" in realm
        assert "clients" in realm

    def test_realm_is_enabled(self):
        """Test generated realm is enabled."""
        realm = generate_keycloak_realm()
        assert realm["enabled"] is True

    def test_default_realm_name(self):
        """Test default realm name is 'iiot'."""
        realm = generate_keycloak_realm()
        assert realm["realm"] == "iiot"
        assert realm["id"] == "iiot"

    def test_custom_realm_name(self):
        """Test custom realm name."""
        realm = generate_keycloak_realm(realm_name="custom-realm")
        assert realm["realm"] == "custom-realm"
        assert realm["id"] == "custom-realm"

    def test_realm_has_display_name(self):
        """Test realm has display name."""
        realm = generate_keycloak_realm()
        assert "IIoT Stack" in realm["displayName"]


class TestRealmRoles:
    """Test Keycloak realm role configuration."""

    def test_realm_has_roles(self):
        """Test realm has roles section."""
        realm = generate_keycloak_realm()
        assert "roles" in realm
        assert "realm" in realm["roles"]

    def test_default_roles_exist(self):
        """Test default roles are created."""
        realm = generate_keycloak_realm()
        realm_roles = realm["roles"]["realm"]

        role_names = [role["name"] for role in realm_roles]
        assert "admin" in role_names
        assert "user" in role_names
        assert "viewer" in role_names

    def test_role_descriptions(self):
        """Test roles have descriptions."""
        realm = generate_keycloak_realm()
        realm_roles = realm["roles"]["realm"]

        for role in realm_roles:
            assert "description" in role
            assert len(role["description"]) > 0


class TestRealmClientScopes:
    """Test Keycloak client scope configuration."""

    def test_realm_has_client_scopes(self):
        """Test realm has client scopes."""
        realm = generate_keycloak_realm()
        assert "clientScopes" in realm
        assert len(realm["clientScopes"]) > 0

    def test_standard_scopes_exist(self):
        """Test standard OIDC scopes exist."""
        realm = generate_keycloak_realm()
        scope_names = [scope["name"] for scope in realm["clientScopes"]]

        assert "roles" in scope_names
        assert "email" in scope_names
        assert "profile" in scope_names

    def test_scopes_have_protocol_mappers(self):
        """Test scopes have protocol mappers."""
        realm = generate_keycloak_realm()

        for scope in realm["clientScopes"]:
            assert "protocolMappers" in scope
            # Each scope should have at least one mapper
            assert len(scope["protocolMappers"]) > 0


class TestRealmUserGeneration:
    """Test Keycloak user generation."""

    def test_no_users_by_default(self):
        """Test no users are created by default."""
        realm = generate_keycloak_realm()
        assert realm["users"] == []

    def test_single_user_creation(self):
        """Test single user creation."""
        users = [
            {
                "username": "testuser",
                "password": "testpass",
                "email": "test@example.com",
                "firstName": "Test",
                "lastName": "User",
                "roles": ["admin"],
            }
        ]
        realm = generate_keycloak_realm(users=users)

        assert len(realm["users"]) == 1
        user = realm["users"][0]
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
        assert user["firstName"] == "Test"
        assert user["lastName"] == "User"

    def test_user_has_credentials(self):
        """Test user has credentials configured."""
        users = [{"username": "admin", "password": "adminpass"}]
        realm = generate_keycloak_realm(users=users)

        user = realm["users"][0]
        assert "credentials" in user
        assert len(user["credentials"]) > 0
        assert user["credentials"][0]["type"] == "password"

    def test_user_default_temporary_password(self):
        """Test user password is temporary by default."""
        users = [{"username": "newuser", "password": "temppass"}]
        realm = generate_keycloak_realm(users=users)

        user = realm["users"][0]
        assert user["credentials"][0]["temporary"] is True
        assert "UPDATE_PASSWORD" in user["requiredActions"]

    def test_user_non_temporary_password(self):
        """Test user with non-temporary password."""
        users = [{"username": "admin", "password": "permanentpass", "temporary": False}]
        realm = generate_keycloak_realm(users=users)

        user = realm["users"][0]
        assert user["credentials"][0]["temporary"] is False
        assert user["requiredActions"] == []

    def test_multiple_users(self):
        """Test multiple user creation."""
        users = [
            {"username": "user1", "password": "pass1"},
            {"username": "user2", "password": "pass2"},
            {"username": "user3", "password": "pass3"},
        ]
        realm = generate_keycloak_realm(users=users)

        assert len(realm["users"]) == 3

    def test_user_email_verification(self):
        """Test user email is verified."""
        users = [{"username": "user", "password": "pass"}]
        realm = generate_keycloak_realm(users=users)

        user = realm["users"][0]
        assert user["emailVerified"] is True
        assert user["enabled"] is True


class TestRealmClientGeneration:
    """Test Keycloak OAuth client generation."""

    def test_no_clients_without_services(self):
        """Test no clients generated without services."""
        realm = generate_keycloak_realm(services=[])
        assert realm["clients"] == []

    def test_grafana_client_generation(self):
        """Test Grafana OAuth client generation."""
        realm = generate_keycloak_realm(services=["grafana"])

        assert len(realm["clients"]) == 1
        client = realm["clients"][0]
        assert client["clientId"] == "grafana"
        assert client["name"] == "Grafana"
        assert client["enabled"] is True
        assert "secret" in client
        assert len(client["secret"]) > 0

    def test_n8n_client_generation(self):
        """Test n8n OAuth client generation."""
        realm = generate_keycloak_realm(services=["n8n"])

        client = realm["clients"][0]
        assert client["clientId"] == "n8n"
        assert "secret" in client

    def test_portainer_client_generation(self):
        """Test Portainer OAuth client generation."""
        realm = generate_keycloak_realm(services=["portainer"])

        client = realm["clients"][0]
        assert client["clientId"] == "portainer"

    def test_ignition_client_generation(self):
        """Test Ignition OAuth client generation."""
        realm = generate_keycloak_realm(services=["ignition"])

        client = realm["clients"][0]
        assert client["clientId"] == "ignition"
        assert "perspective" in str(client["redirectUris"]).lower() or "ignition" in str(client["redirectUris"]).lower()

    def test_multiple_clients(self):
        """Test multiple client generation."""
        services = ["grafana", "n8n", "portainer"]
        realm = generate_keycloak_realm(services=services)

        assert len(realm["clients"]) == 3
        client_ids = [c["clientId"] for c in realm["clients"]]
        assert "grafana" in client_ids
        assert "n8n" in client_ids
        assert "portainer" in client_ids

    def test_client_has_secret(self):
        """Test all clients have secrets."""
        services = ["grafana", "n8n", "portainer", "ignition"]
        realm = generate_keycloak_realm(services=services)

        for client in realm["clients"]:
            assert "secret" in client
            assert len(client["secret"]) > 0

    def test_clients_have_unique_secrets(self):
        """Test all clients have unique secrets."""
        services = ["grafana", "n8n", "portainer", "ignition"]
        realm = generate_keycloak_realm(services=services)

        secrets = [client["secret"] for client in realm["clients"]]
        assert len(set(secrets)) == len(secrets)


class TestRealmClientConfiguration:
    """Test detailed client configuration."""

    def test_client_protocol_settings(self):
        """Test client protocol settings."""
        realm = generate_keycloak_realm(services=["grafana"])
        client = realm["clients"][0]

        assert client["protocol"] == "openid-connect"
        assert client["publicClient"] is False
        assert client["directAccessGrantsEnabled"] is True
        assert client["standardFlowEnabled"] is True

    def test_client_redirect_uris(self):
        """Test client redirect URIs."""
        realm = generate_keycloak_realm(
            services=["grafana"],
            base_domain="example.com"
        )
        client = realm["clients"][0]

        assert "redirectUris" in client
        assert len(client["redirectUris"]) > 0
        # Should include domain
        assert any("example.com" in uri for uri in client["redirectUris"])

    def test_client_redirect_uris_https(self):
        """Test client redirect URIs with HTTPS."""
        realm = generate_keycloak_realm(
            services=["grafana"],
            base_domain="secure.example.com",
            enable_https=True
        )
        client = realm["clients"][0]

        # Should use https protocol
        assert any("https://" in uri for uri in client["redirectUris"])

    def test_client_web_origins(self):
        """Test client web origins."""
        realm = generate_keycloak_realm(services=["grafana"])
        client = realm["clients"][0]

        assert "webOrigins" in client
        # "+" means all redirect URIs are allowed
        assert "+" in client["webOrigins"]

    def test_client_default_scopes(self):
        """Test client default scopes."""
        realm = generate_keycloak_realm(services=["grafana"])
        client = realm["clients"][0]

        assert "defaultClientScopes" in client
        scopes = client["defaultClientScopes"]
        assert "email" in scopes
        assert "profile" in scopes
        assert "roles" in scopes


class TestRealmSerialization:
    """Test realm JSON serialization."""

    def test_realm_is_json_serializable(self):
        """Test realm can be serialized to JSON."""
        realm = generate_keycloak_realm(
            services=["grafana", "n8n"],
            users=[{"username": "admin", "password": "admin"}]
        )

        # Should not raise
        json_str = json.dumps(realm)
        assert len(json_str) > 0

    def test_realm_roundtrip(self):
        """Test realm JSON roundtrip."""
        realm = generate_keycloak_realm(services=["grafana"])

        json_str = json.dumps(realm)
        parsed = json.loads(json_str)

        assert parsed["realm"] == realm["realm"]
        assert len(parsed["clients"]) == len(realm["clients"])


class TestReadmeSectionGeneration:
    """Test Keycloak README section generation."""

    def test_readme_contains_realm_name(self):
        """Test README contains realm name."""
        clients = [{"clientId": "grafana", "name": "Grafana", "secret": "secret123"}]
        content = generate_keycloak_readme_section("test-realm", clients)

        assert "test-realm" in content

    def test_readme_lists_clients(self):
        """Test README lists all clients."""
        clients = [
            {"clientId": "grafana", "name": "Grafana", "secret": "secret1"},
            {"clientId": "n8n", "name": "n8n", "secret": "secret2"},
        ]
        content = generate_keycloak_readme_section("iiot", clients)

        assert "grafana" in content
        assert "n8n" in content

    def test_readme_does_not_expose_secrets(self):
        """Test README does not expose client secrets."""
        clients = [{"clientId": "grafana", "name": "Grafana", "secret": "supersecret123"}]
        content = generate_keycloak_readme_section("iiot", clients)

        # Secret should not appear
        assert "supersecret123" not in content
        # But should reference .env file
        assert ".env" in content or "admin console" in content.lower()

    def test_readme_has_instructions(self):
        """Test README has setup instructions."""
        clients = [{"clientId": "grafana", "name": "Grafana", "secret": "secret"}]
        content = generate_keycloak_readme_section("iiot", clients)

        # Should have some form of instructions
        assert "Admin" in content or "access" in content.lower()

    def test_readme_mentions_roles(self):
        """Test README mentions available roles."""
        clients = []
        content = generate_keycloak_readme_section("iiot", clients)

        assert "admin" in content.lower()
        assert "user" in content.lower()
        assert "viewer" in content.lower()

    def test_readme_is_markdown(self):
        """Test README is valid markdown."""
        clients = [{"clientId": "grafana", "name": "Grafana", "secret": "secret"}]
        content = generate_keycloak_readme_section("iiot", clients)

        # Should have markdown headers
        assert "##" in content
        # Should have some markdown formatting
        assert "`" in content or "**" in content

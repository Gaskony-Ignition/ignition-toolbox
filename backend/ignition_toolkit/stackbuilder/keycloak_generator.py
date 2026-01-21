"""
Keycloak realm configuration generator

Generates realm-import.json for automatic OAuth/SSO setup with pre-generated
client secrets for integrated services like Grafana, n8n, and Portainer.
"""

import secrets
from typing import Any


def generate_client_secret() -> str:
    """Generate a secure client secret"""
    return secrets.token_urlsafe(32)


def generate_keycloak_realm(
    realm_name: str = "iiot",
    services: list[str] | None = None,
    users: list[dict[str, Any]] | None = None,
    base_domain: str = "localhost",
    enable_https: bool = False,
) -> dict[str, Any]:
    """
    Generate a complete Keycloak realm configuration

    Args:
        realm_name: Name of the realm
        services: List of service IDs that need OAuth clients
        users: List of users to import
        base_domain: Base domain for redirect URIs
        enable_https: Whether to use HTTPS URLs

    Returns:
        Complete realm configuration as dict
    """
    services = services or []
    users = users or []
    protocol = "https" if enable_https else "http"

    # Base realm configuration
    realm: dict[str, Any] = {
        "id": realm_name,
        "realm": realm_name,
        "displayName": "IIoT Stack",
        "displayNameHtml": '<div class="kc-logo-text"><span>IIoT Stack</span></div>',
        "enabled": True,
        "sslRequired": "external",
        "registrationAllowed": False,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False,
        "resetPasswordAllowed": True,
        "editUsernameAllowed": False,
        "bruteForceProtected": True,
        # Session settings
        "ssoSessionIdleTimeout": 1800,
        "ssoSessionMaxLifespan": 36000,
        "offlineSessionIdleTimeout": 2592000,
        # Token settings
        "accessTokenLifespan": 300,
        "accessTokenLifespanForImplicitFlow": 900,
        "accessCodeLifespan": 60,
        "accessCodeLifespanUserAction": 300,
        # Roles
        "roles": {
            "realm": [
                {
                    "name": "admin",
                    "description": "Administrator role with full access",
                    "composite": False,
                },
                {
                    "name": "user",
                    "description": "Standard user role",
                    "composite": False,
                },
                {
                    "name": "viewer",
                    "description": "Read-only access",
                    "composite": False,
                },
            ],
            "client": {},
        },
        # Client scopes
        "clientScopes": [
            {
                "name": "roles",
                "description": "OpenID Connect scope for user roles",
                "protocol": "openid-connect",
                "attributes": {
                    "include.in.token.scope": "true",
                    "display.on.consent.screen": "true",
                },
                "protocolMappers": [
                    {
                        "name": "realm roles",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-usermodel-realm-role-mapper",
                        "config": {
                            "multivalued": "true",
                            "userinfo.token.claim": "true",
                            "id.token.claim": "true",
                            "access.token.claim": "true",
                            "claim.name": "roles",
                            "jsonType.label": "String",
                        },
                    }
                ],
            },
            {
                "name": "email",
                "description": "OpenID Connect built-in scope: email",
                "protocol": "openid-connect",
                "attributes": {
                    "include.in.token.scope": "true",
                    "display.on.consent.screen": "true",
                },
                "protocolMappers": [
                    {
                        "name": "email",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-usermodel-property-mapper",
                        "config": {
                            "userinfo.token.claim": "true",
                            "user.attribute": "email",
                            "id.token.claim": "true",
                            "access.token.claim": "true",
                            "claim.name": "email",
                            "jsonType.label": "String",
                        },
                    }
                ],
            },
            {
                "name": "profile",
                "description": "OpenID Connect built-in scope: profile",
                "protocol": "openid-connect",
                "attributes": {
                    "include.in.token.scope": "true",
                    "display.on.consent.screen": "true",
                },
                "protocolMappers": [
                    {
                        "name": "given name",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-usermodel-property-mapper",
                        "config": {
                            "userinfo.token.claim": "true",
                            "user.attribute": "firstName",
                            "id.token.claim": "true",
                            "access.token.claim": "true",
                            "claim.name": "given_name",
                            "jsonType.label": "String",
                        },
                    },
                    {
                        "name": "family name",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-usermodel-property-mapper",
                        "config": {
                            "userinfo.token.claim": "true",
                            "user.attribute": "lastName",
                            "id.token.claim": "true",
                            "access.token.claim": "true",
                            "claim.name": "family_name",
                            "jsonType.label": "String",
                        },
                    },
                ],
            },
        ],
        "users": [],
        "clients": [],
    }

    # Add users
    for user in users:
        realm["users"].append(_generate_user(user, realm_name))

    # Add OAuth clients for each service
    clients = []

    if "grafana" in services:
        clients.append(_generate_grafana_client(base_domain, protocol))

    if "n8n" in services:
        clients.append(_generate_n8n_client(base_domain, protocol))

    if "portainer" in services:
        clients.append(_generate_portainer_client(base_domain, protocol))

    if "ignition" in services:
        clients.append(_generate_ignition_client(base_domain, protocol))

    realm["clients"] = clients

    return realm


def _generate_user(user_data: dict[str, Any], realm_name: str) -> dict[str, Any]:
    """Generate a Keycloak user object"""
    username = user_data.get("username", "")
    password = user_data.get("password", "changeme")
    email = user_data.get("email", f"{username}@{realm_name}.local")
    first_name = user_data.get("firstName", username.capitalize())
    last_name = user_data.get("lastName", "User")

    roles = user_data.get("roles", ["user"])
    if not isinstance(roles, list):
        roles = [roles]

    return {
        "username": username,
        "enabled": True,
        "emailVerified": True,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "credentials": [
            {
                "type": "password",
                "value": password,
                "temporary": user_data.get("temporary", True),
            }
        ],
        "realmRoles": roles,
        "requiredActions": (
            ["UPDATE_PASSWORD"] if user_data.get("temporary", True) else []
        ),
    }


def _generate_grafana_client(base_domain: str, protocol: str) -> dict[str, Any]:
    """Generate Grafana OAuth client configuration"""
    client_secret = generate_client_secret()
    redirect_uri = f"{protocol}://grafana.{base_domain}/*"

    return {
        "clientId": "grafana",
        "name": "Grafana",
        "description": "Grafana Analytics Platform",
        "enabled": True,
        "clientAuthenticatorType": "client-secret",
        "secret": client_secret,
        "redirectUris": [
            redirect_uri,
            f"{protocol}://grafana.{base_domain}/login/generic_oauth",
        ],
        "webOrigins": ["+"],
        "protocol": "openid-connect",
        "publicClient": False,
        "directAccessGrantsEnabled": True,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "serviceAccountsEnabled": False,
        "authorizationServicesEnabled": False,
        "fullScopeAllowed": True,
        "defaultClientScopes": ["email", "profile", "roles"],
        "optionalClientScopes": [],
        "protocolMappers": [
            {
                "name": "grafana-role-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-realm-role-mapper",
                "config": {
                    "claim.name": "roles",
                    "jsonType.label": "String",
                    "multivalued": "true",
                    "userinfo.token.claim": "true",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                },
            }
        ],
    }


def _generate_n8n_client(base_domain: str, protocol: str) -> dict[str, Any]:
    """Generate n8n OAuth client configuration"""
    client_secret = generate_client_secret()

    return {
        "clientId": "n8n",
        "name": "n8n Workflow Automation",
        "enabled": True,
        "clientAuthenticatorType": "client-secret",
        "secret": client_secret,
        "redirectUris": [
            f"{protocol}://n8n.{base_domain}/*",
            f"{protocol}://n8n.{base_domain}/rest/oauth2-credential/callback",
        ],
        "webOrigins": ["+"],
        "protocol": "openid-connect",
        "publicClient": False,
        "directAccessGrantsEnabled": True,
        "standardFlowEnabled": True,
        "fullScopeAllowed": True,
        "defaultClientScopes": ["email", "profile", "roles"],
    }


def _generate_portainer_client(base_domain: str, protocol: str) -> dict[str, Any]:
    """Generate Portainer OAuth client configuration"""
    client_secret = generate_client_secret()

    return {
        "clientId": "portainer",
        "name": "Portainer",
        "enabled": True,
        "clientAuthenticatorType": "client-secret",
        "secret": client_secret,
        "redirectUris": [f"{protocol}://portainer.{base_domain}/*"],
        "webOrigins": ["+"],
        "protocol": "openid-connect",
        "publicClient": False,
        "directAccessGrantsEnabled": True,
        "standardFlowEnabled": True,
        "fullScopeAllowed": True,
        "defaultClientScopes": ["email", "profile", "roles"],
    }


def _generate_ignition_client(base_domain: str, protocol: str) -> dict[str, Any]:
    """Generate Ignition OAuth client configuration"""
    client_secret = generate_client_secret()

    return {
        "clientId": "ignition",
        "name": "Ignition SCADA",
        "enabled": True,
        "clientAuthenticatorType": "client-secret",
        "secret": client_secret,
        "redirectUris": [
            f"{protocol}://ignition.{base_domain}/*",
            f"{protocol}://ignition.{base_domain}/data/perspective/client/*",
        ],
        "webOrigins": ["+"],
        "protocol": "openid-connect",
        "publicClient": False,
        "directAccessGrantsEnabled": True,
        "standardFlowEnabled": True,
        "fullScopeAllowed": True,
        "defaultClientScopes": ["email", "profile", "roles"],
    }


def generate_keycloak_readme_section(
    realm_name: str, clients: list[dict[str, Any]]
) -> str:
    """
    Generate README section with Keycloak setup instructions.

    Note: Client secrets are NOT included in the README for security.
    They can be found in the .env file or Keycloak admin console.

    Args:
        realm_name: The Keycloak realm name
        clients: List of OAuth client configurations

    Returns:
        Markdown content for the README
    """
    content = f"""
## Keycloak SSO Configuration

Your stack includes automatic Keycloak realm configuration for Single Sign-On (SSO).

### Realm Import

The realm configuration is automatically imported on first startup.

**Realm Name:** `{realm_name}`

### OAuth Client Credentials

The following OAuth clients have been configured:

"""

    for client in clients:
        client_id = client.get("clientId")
        # Don't expose secrets in README - reference .env file instead
        content += f"""
#### {client.get("name", client_id)}
- **Client ID:** `{client_id}`
- **Client Secret:** See `.env` file or Keycloak admin console
- **Scopes:** openid, profile, email, roles

"""

    content += f"""
> **Security Note:** Client secrets are stored in the `.env` file.
> Keep this file secure and never commit it to version control.

### Accessing Keycloak Admin Console

1. Navigate to Keycloak: `http://keycloak.localhost` (or your configured domain)
2. Login with admin credentials (from your `.env` file)
3. Select the `{realm_name}` realm from the dropdown

### Default Roles

Three realm roles are available:
- **admin** - Full administrative access
- **user** - Standard user access
- **viewer** - Read-only access

Assign roles in Admin Console -> Users -> Role Mappings.
"""

    return content

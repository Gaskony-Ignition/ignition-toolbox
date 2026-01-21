# Stack Builder Module

The Stack Builder is a Docker Compose generator for IIoT/SCADA infrastructure. It provides a visual interface for selecting and configuring services, automatically detecting integrations between them, and generating production-ready deployment configurations.

## Features

- **Service Catalog**: Browse 25+ pre-configured services including Ignition, databases, MQTT brokers, monitoring tools, and more
- **Automatic Integration Detection**: Automatically detects and configures connections between services (e.g., database connections, MQTT clients, OAuth providers)
- **Configuration Generation**: Generates complete deployment packages including:
  - `docker-compose.yml`
  - `.env` file with all credentials
  - Service-specific configuration files
  - Startup scripts for Linux and Windows
  - README with setup instructions

## Architecture

```
stackbuilder/
├── __init__.py           # Module exports
├── catalog.py            # Service catalog management
├── compose_generator.py  # Docker Compose generation
├── config_generators.py  # Service configuration file generation
├── integration_engine.py # Integration detection logic
├── keycloak_generator.py # Keycloak realm configuration
├── ignition_db_registration.py # Ignition DB setup scripts
├── exceptions.py         # Custom exception hierarchy
├── types.py              # TypedDict definitions
└── data/
    ├── catalog.json      # Service definitions
    └── integrations.json # Integration patterns
```

## Usage

### Basic Stack Generation

```python
from ignition_toolkit.stackbuilder import ComposeGenerator, ServiceCatalog

# Create generator
generator = ComposeGenerator()

# Define instances
instances = [
    {"app_id": "ignition", "instance_name": "ignition-1", "config": {}},
    {"app_id": "postgres", "instance_name": "postgres-1", "config": {"database": "ignition_db"}},
]

# Generate stack
result = generator.generate(instances)

print(result["docker_compose"])  # docker-compose.yml content
print(result["env_file"])        # .env file content
print(result["readme"])          # README.md content
```

### With Global Settings

```python
from ignition_toolkit.stackbuilder.compose_generator import (
    ComposeGenerator,
    GlobalSettings,
    IntegrationSettings,
)

generator = ComposeGenerator()

global_settings = GlobalSettings(
    stack_name="my-iiot-stack",
    timezone="America/New_York",
    restart_policy="always",
)

integration_settings = IntegrationSettings(
    reverse_proxy={"base_domain": "example.com", "enable_https": True},
    oauth={"realm_name": "production", "auto_configure_services": True},
)

result = generator.generate(
    instances,
    global_settings=global_settings,
    integration_settings=integration_settings,
)
```

### Generate ZIP Bundle

```python
zip_bytes = generator.generate_zip(instances)
with open("my-stack.zip", "wb") as f:
    f.write(zip_bytes)
```

## Service Categories

| Category | Services |
|----------|----------|
| Industrial Platforms | Ignition |
| Databases | PostgreSQL, MariaDB, MSSQL |
| Messaging & Brokers | EMQX, Mosquitto |
| Authentication | Keycloak, Authentik, Authelia |
| Networking / Proxy | Traefik, Nginx Proxy Manager |
| Monitoring | Grafana, Prometheus, Dozzle |
| Automation / Workflow | Node-RED, n8n |
| DevOps Tools | Portainer, MailHog, WhatUpDocker |
| Version Control | GitLab, Gitea |

## Integration Types

The integration engine automatically detects and configures:

- **Database Connections**: Configures Ignition to connect to PostgreSQL/MariaDB
- **MQTT Broker Clients**: Sets up MQTT connections for Ignition and other services
- **OAuth/SSO**: Configures Keycloak clients for Grafana, n8n, and other services
- **Email/SMTP**: Connects services to MailHog for email testing
- **Reverse Proxy**: Generates Traefik labels and routing configuration
- **Monitoring**: Sets up Grafana datasources for databases and Prometheus

## API Endpoints

The Stack Builder exposes the following REST API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stackbuilder/catalog` | GET | Get full service catalog |
| `/api/stackbuilder/catalog/{app_id}` | GET | Get specific application details |
| `/api/stackbuilder/versions/{app_id}` | GET | Get available versions for an application |
| `/api/stackbuilder/detect-integrations` | POST | Detect integrations for a stack configuration |
| `/api/stackbuilder/generate` | POST | Generate stack configuration (JSON response) |
| `/api/stackbuilder/download` | POST | Generate and download stack as ZIP |
| `/api/stackbuilder/stacks` | GET/POST | List/save stack configurations |
| `/api/stackbuilder/stacks/{id}` | GET/DELETE | Get/delete a saved stack |

## Security Considerations

1. **Passwords**: All default passwords in the catalog are for development only. The generator creates random secrets for OAuth clients.

2. **Mosquitto**: Passwords are hashed using PBKDF2-SHA512 (Mosquitto 2.0+ format)

3. **Traefik Dashboard**: Secured by default (`insecure: false`). Configure authentication middleware for production access.

4. **Generated Files**: The `.env` file contains sensitive credentials. Never commit it to version control.

5. **Keycloak**: Runs in development mode by default. Change to production mode (`start` instead of `start-dev`) for production deployments.

## Extending the Catalog

To add a new service, add an entry to `data/catalog.json`:

```json
{
  "id": "my-service",
  "name": "My Service",
  "category": "DevOps Tools",
  "description": "Description of the service",
  "image": "myorg/myservice",
  "default_version": "latest",
  "available_versions": ["latest", "1.0", "0.9"],
  "supports_multiple": false,
  "default_config": {
    "ports": ["8080:8080"],
    "environment": {"KEY": "value"},
    "volumes": ["{instance_name}-data:/data"]
  },
  "configurable_options": {
    "port": {"type": "number", "default": 8080, "label": "HTTP Port"}
  },
  "integrations": ["db_client"],
  "enabled": true
}
```

## Exception Hierarchy

```
StackBuilderError
├── CatalogError
│   ├── CatalogNotFoundError
│   ├── ServiceNotFoundError
│   └── ServiceDisabledError
├── IntegrationError
│   └── IntegrationConflictError
├── GenerationError
│   └── ConfigurationError
└── ValidationError
    ├── InvalidNameError
    └── ReservedNameError
```

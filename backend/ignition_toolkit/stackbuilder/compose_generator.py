"""
Docker Compose Generator for Stack Builder

Generates docker-compose.yml and related configuration files.
"""

import io
import json
import logging
import zipfile
from typing import Any

import yaml

from ignition_toolkit.stackbuilder.catalog import get_service_catalog
from ignition_toolkit.stackbuilder.config_generators import (
    generate_grafana_datasources,
    generate_mosquitto_config,
    generate_prometheus_config,
    generate_traefik_dynamic_config,
    generate_traefik_static_config,
)
from ignition_toolkit.stackbuilder.integration_engine import get_integration_engine

logger = logging.getLogger(__name__)


class GlobalSettings:
    """Global settings for the stack"""

    def __init__(
        self,
        stack_name: str = "iiot-stack",
        timezone: str = "UTC",
        restart_policy: str = "unless-stopped",
    ):
        self.stack_name = stack_name
        self.timezone = timezone
        self.restart_policy = restart_policy


class IntegrationSettings:
    """Settings for automatic integrations"""

    def __init__(
        self,
        reverse_proxy: dict | None = None,
        mqtt: dict | None = None,
        oauth: dict | None = None,
        database: dict | None = None,
        email: dict | None = None,
    ):
        self.reverse_proxy = reverse_proxy or {
            "base_domain": "localhost",
            "enable_https": False,
            "letsencrypt_email": "",
        }
        self.mqtt = mqtt or {
            "enable_tls": False,
            "username": "",
            "password": "",
            "tls_port": 8883,
        }
        self.oauth = oauth or {
            "realm_name": "iiot",
            "auto_configure_services": True,
        }
        self.database = database or {"auto_register": True}
        self.email = email or {
            "from_address": "noreply@iiot.local",
            "auto_configure_services": True,
        }


class ComposeGenerator:
    """
    Generator for Docker Compose configurations

    Takes a list of service instances and generates:
    - docker-compose.yml
    - .env file
    - Configuration files for services
    - README documentation
    """

    def __init__(self):
        self.catalog = get_service_catalog()
        self.engine = get_integration_engine()

    def generate(
        self,
        instances: list[dict[str, Any]],
        global_settings: GlobalSettings | None = None,
        integration_settings: IntegrationSettings | None = None,
    ) -> dict[str, Any]:
        """
        Generate docker-compose configuration

        Args:
            instances: List of service instance configs
            global_settings: Global stack settings
            integration_settings: Integration configuration settings

        Returns:
            Dict with docker_compose, env, readme, and config_files
        """
        if global_settings is None:
            global_settings = GlobalSettings()
        if integration_settings is None:
            integration_settings = IntegrationSettings()

        catalog_dict = self.catalog.get_application_as_dict()

        # Detect integrations
        instances_for_detection = [
            {
                "app_id": inst["app_id"],
                "instance_name": inst["instance_name"],
                "config": inst.get("config", {}),
            }
            for inst in instances
        ]
        integration_results = self.engine.detect_integrations(instances_for_detection)

        # Build docker compose structure
        stack_name = global_settings.stack_name
        compose: dict[str, Any] = {
            "name": stack_name,
            "services": {},
            "networks": {f"{stack_name}-network": {"driver": "bridge"}},
            "volumes": {},
        }

        # Track generated config files
        config_files: dict[str, str] = {}
        env_vars: list[str] = []

        env_vars.append("# Global Settings")
        env_vars.append(f"TZ={global_settings.timezone}")
        env_vars.append(f"RESTART_POLICY={global_settings.restart_policy}")
        env_vars.append("")

        # Check what's in the stack
        has_traefik = any(inst["app_id"] == "traefik" for inst in instances)

        # Process each instance
        for instance in instances:
            app = catalog_dict.get(instance["app_id"])
            if not app or not app.get("enabled", False):
                continue

            service_name = instance["instance_name"]
            config = instance.get("config", {})

            # Build image name with version
            version = config.get("version", app.get("default_version", "latest"))
            image = f"{app['image']}:{version}"

            # Create service definition
            service: dict[str, Any] = {
                "image": image,
                "container_name": f"{stack_name}-{service_name}",
                "networks": [f"{stack_name}-network"],
                "restart": global_settings.restart_policy,
            }

            # Handle ports
            if "ports" in app.get("default_config", {}):
                ports = []
                for port_mapping in app["default_config"]["ports"]:
                    if ":" in port_mapping:
                        container_port = port_mapping.split(":")[1]
                        host_port = config.get("port", port_mapping.split(":")[0])
                        ports.append(f"{host_port}:{container_port}")
                    else:
                        ports.append(port_mapping)
                service["ports"] = ports

            # Handle environment variables
            if "environment" in app.get("default_config", {}):
                env = app["default_config"]["environment"].copy()
                env["TZ"] = global_settings.timezone

                # Apply app-specific config mappings
                self._apply_app_config(instance["app_id"], config, env)

                service["environment"] = env

            # Handle volumes
            if "volumes" in app.get("default_config", {}):
                volumes = []
                for vol in app["default_config"]["volumes"]:
                    vol = vol.replace("{instance_name}", service_name)
                    volumes.append(vol)
                service["volumes"] = volumes

            # Handle command
            if "command" in app.get("default_config", {}):
                service["command"] = app["default_config"]["command"]

            # Handle cap_add
            if "cap_add" in app.get("default_config", {}):
                service["cap_add"] = app["default_config"]["cap_add"]

            # Add Traefik labels if applicable
            if has_traefik and instance["app_id"] != "traefik":
                labels = self._generate_traefik_labels(
                    instance, integration_settings.reverse_proxy
                )
                if labels:
                    service["labels"] = labels

            compose["services"][service_name] = service

            # Add to env file
            env_vars.append(f"# {service_name}")
            env_vars.append(f"{service_name.upper().replace('-', '_')}_VERSION={version}")
            env_vars.append("")

        # Collect named volumes
        named_volumes = set()
        for service_name, service in compose["services"].items():
            if "volumes" in service:
                for vol in service["volumes"]:
                    if ":" in vol:
                        volume_part = vol.split(":")[0]
                        if not volume_part.startswith("./") and not volume_part.startswith("/"):
                            named_volumes.add(volume_part)

        if named_volumes:
            for vol_name in sorted(named_volumes):
                compose["volumes"][vol_name] = None

        # Generate integration config files
        self._generate_integration_configs(
            instances, integration_results, integration_settings, config_files
        )

        # Generate Prometheus configs for any Prometheus instances
        for instance in instances:
            if instance["app_id"] == "prometheus":
                config_files[f"configs/{instance['instance_name']}/prometheus.yml"] = (
                    generate_prometheus_config()
                )

        # Convert to YAML
        compose_yaml = yaml.dump(compose, default_flow_style=False, sort_keys=False)
        env_content = "\n".join(env_vars)

        # Generate README
        readme_content = self._generate_readme(instances, global_settings, catalog_dict)

        return {
            "docker_compose": compose_yaml,
            "env": env_content,
            "readme": readme_content,
            "config_files": config_files,
            "integration_results": integration_results,
        }

    def generate_zip(
        self,
        instances: list[dict[str, Any]],
        global_settings: GlobalSettings | None = None,
        integration_settings: IntegrationSettings | None = None,
    ) -> bytes:
        """
        Generate a ZIP file containing all stack files

        Returns:
            ZIP file content as bytes
        """
        generated = self.generate(instances, global_settings, integration_settings)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("docker-compose.yml", generated["docker_compose"])
            zip_file.writestr(".env", generated["env"])
            zip_file.writestr("README.md", generated["readme"])

            for file_path, content in generated.get("config_files", {}).items():
                info = zipfile.ZipInfo(file_path)
                info.external_attr = 0o644 << 16
                zip_file.writestr(info, content)

            zip_file.writestr("configs/.gitkeep", "")

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    def _apply_app_config(self, app_id: str, config: dict, env: dict) -> None:
        """Apply app-specific configuration mappings"""
        if app_id == "postgres":
            env["POSTGRES_DB"] = config.get("database", env.get("POSTGRES_DB"))
            env["POSTGRES_USER"] = config.get("username", env.get("POSTGRES_USER"))
            env["POSTGRES_PASSWORD"] = config.get("password", env.get("POSTGRES_PASSWORD"))

        elif app_id == "mariadb":
            env["MYSQL_DATABASE"] = config.get("database", env.get("MYSQL_DATABASE"))
            env["MYSQL_USER"] = config.get("username", env.get("MYSQL_USER"))
            env["MYSQL_PASSWORD"] = config.get("password", env.get("MYSQL_PASSWORD"))
            env["MYSQL_ROOT_PASSWORD"] = config.get("root_password", env.get("MYSQL_ROOT_PASSWORD"))

        elif app_id == "ignition":
            env["GATEWAY_ADMIN_USERNAME"] = config.get("admin_username", env.get("GATEWAY_ADMIN_USERNAME"))
            env["GATEWAY_ADMIN_PASSWORD"] = config.get("admin_password", env.get("GATEWAY_ADMIN_PASSWORD"))
            env["IGNITION_EDITION"] = config.get("edition", env.get("IGNITION_EDITION", "standard"))

            modules = config.get("modules", [])
            if isinstance(modules, list) and len(modules) > 0:
                module_values = []
                for mod in modules:
                    if isinstance(mod, dict):
                        module_values.append(mod.get("value", mod))
                    else:
                        module_values.append(mod)
                env["GATEWAY_MODULES_ENABLED"] = ",".join(module_values)

        elif app_id == "grafana":
            env["GF_SECURITY_ADMIN_USER"] = config.get("admin_username", env.get("GF_SECURITY_ADMIN_USER"))
            env["GF_SECURITY_ADMIN_PASSWORD"] = config.get("admin_password", env.get("GF_SECURITY_ADMIN_PASSWORD"))

        elif app_id == "keycloak":
            env["KEYCLOAK_ADMIN"] = config.get("admin_username", env.get("KEYCLOAK_ADMIN"))
            env["KEYCLOAK_ADMIN_PASSWORD"] = config.get("admin_password", env.get("KEYCLOAK_ADMIN_PASSWORD"))

    def _generate_traefik_labels(
        self, instance: dict, reverse_proxy_settings: dict
    ) -> list[str] | None:
        """Generate Traefik labels for a web service"""
        web_service_ports = {
            "ignition": lambda c: str(c.get("http_port", 8088)),
            "grafana": lambda c: str(c.get("port", 3000)),
            "nodered": lambda c: str(c.get("port", 1880)),
            "n8n": lambda c: str(c.get("port", 5678)),
            "keycloak": lambda c: str(c.get("port", 8180)),
            "prometheus": lambda c: "9090",
            "dozzle": lambda c: "8080",
            "portainer": lambda c: "9000",
        }

        app_id = instance["app_id"]
        if app_id not in web_service_ports:
            return None

        service_name = instance["instance_name"]
        config = instance.get("config", {})

        subdomain = service_name.split("-")[0] if "-" in service_name else service_name
        port = web_service_ports[app_id](config)
        base_domain = reverse_proxy_settings.get("base_domain", "localhost")
        enable_https = reverse_proxy_settings.get("enable_https", False)
        entrypoint = "websecure" if enable_https else "web"

        labels = [
            "traefik.enable=true",
            f"traefik.http.routers.{service_name}.rule=Host(`{subdomain}.{base_domain}`)",
            f"traefik.http.routers.{service_name}.entrypoints={entrypoint}",
            f"traefik.http.services.{service_name}.loadbalancer.server.port={port}",
        ]

        if enable_https:
            labels.append(f"traefik.http.routers.{service_name}.tls=true")
            labels.append(f"traefik.http.routers.{service_name}.tls.certresolver=letsencrypt")

        return labels

    def _generate_integration_configs(
        self,
        instances: list[dict],
        integration_results: dict,
        integration_settings: IntegrationSettings,
        config_files: dict[str, str],
    ) -> None:
        """Generate configuration files for integrations"""
        integrations = integration_results.get("integrations", {})

        # MQTT Broker Configuration
        if "mqtt_broker" in integrations:
            mqtt_int = integrations["mqtt_broker"]
            for provider_info in mqtt_int.get("providers", []):
                provider_id = provider_info["service_id"]
                instance_name = provider_info["instance_name"]

                if provider_id == "mosquitto":
                    mqtt_username = integration_settings.mqtt.get("username", "")
                    mqtt_password = integration_settings.mqtt.get("password", "")
                    mqtt_enable_tls = integration_settings.mqtt.get("enable_tls", False)
                    mqtt_tls_port = integration_settings.mqtt.get("tls_port", 8883)

                    config_files[f"configs/{instance_name}/mosquitto.conf"] = (
                        generate_mosquitto_config(
                            username=mqtt_username,
                            password=mqtt_password,
                            enable_tls=mqtt_enable_tls,
                            tls_port=mqtt_tls_port,
                        )
                    )

        # Grafana Datasource Provisioning
        if "visualization" in integrations:
            viz_int = integrations["visualization"]
            grafana_instance = viz_int.get("provider")

            if grafana_instance:
                datasources_config = []

                for ds in viz_int.get("datasources", []):
                    datasources_config.append({
                        "type": ds["service_id"],
                        "instance_name": ds["instance_name"],
                        "config": ds["config"],
                    })

                if datasources_config:
                    config_files[f"configs/{grafana_instance}/provisioning/datasources/auto.yaml"] = (
                        generate_grafana_datasources(datasources_config)
                    )

        # Traefik Configuration
        has_traefik = any(inst["app_id"] == "traefik" for inst in instances)
        if has_traefik:
            enable_https = integration_settings.reverse_proxy.get("enable_https", False)
            letsencrypt_email = integration_settings.reverse_proxy.get("letsencrypt_email", "")

            config_files["configs/traefik/traefik.yml"] = generate_traefik_static_config(
                enable_https=enable_https,
                letsencrypt_email=letsencrypt_email,
            )

            # Generate dynamic routing for web services
            services_for_traefik = []
            web_service_ports = {
                "ignition": lambda c: int(c.get("http_port", 8088)),
                "grafana": lambda c: int(c.get("port", 3000)),
                "nodered": lambda c: int(c.get("port", 1880)),
                "n8n": lambda c: int(c.get("port", 5678)),
                "keycloak": lambda c: int(c.get("port", 8180)),
                "prometheus": lambda c: 9090,
            }

            for instance in instances:
                if instance["app_id"] != "traefik" and instance["app_id"] in web_service_ports:
                    service_name = instance["instance_name"]
                    config = instance.get("config", {})
                    subdomain = service_name.split("-")[0] if "-" in service_name else service_name
                    port = web_service_ports[instance["app_id"]](config)

                    services_for_traefik.append({
                        "instance_name": service_name,
                        "subdomain": subdomain,
                        "port": port,
                    })

            base_domain = integration_settings.reverse_proxy.get("base_domain", "localhost")
            config_files["configs/traefik/dynamic/services.yml"] = generate_traefik_dynamic_config(
                services=services_for_traefik,
                domain=base_domain,
                enable_https=enable_https,
            )

    def _generate_readme(
        self,
        instances: list[dict],
        global_settings: GlobalSettings,
        catalog_dict: dict,
    ) -> str:
        """Generate README documentation"""
        readme = f"""# {global_settings.stack_name} - Generated Configuration

## Global Settings
- **Stack Name**: {global_settings.stack_name}
- **Timezone**: {global_settings.timezone}
- **Restart Policy**: {global_settings.restart_policy}

## Services Included
"""
        for instance in instances:
            version = instance.get("config", {}).get("version", "latest")
            readme += f"- {instance['instance_name']} ({instance['app_id']}) - {version}\n"

        readme += """
## Getting Started

1. Review the generated `docker-compose.yml` and `.env` files
2. Customize any settings as needed
3. Start the stack:
   ```bash
   docker compose up -d
   ```

## Service URLs
"""
        for instance in instances:
            app = catalog_dict.get(instance["app_id"])
            if app and "ports" in app.get("default_config", {}):
                config = instance.get("config", {})
                port = config.get("port", config.get("http_port", 8080))
                readme += f"- **{instance['instance_name']}**: http://localhost:{port}\n"

        readme += """
## Stopping the Stack

```bash
docker compose down
```

To remove volumes as well:
```bash
docker compose down -v
```

## Generated by Ignition Toolbox Stack Builder
"""
        return readme

"""
Integration Engine for Stack Builder

Handles automatic service integration detection and configuration generation.
Ported from ignition-stack-builder project.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class IntegrationEngine:
    """Core engine for managing service integrations"""

    def __init__(self, integrations_path: Path | None = None):
        """
        Initialize the integration engine

        Args:
            integrations_path: Path to integrations.json. If None, uses default.
        """
        if integrations_path is None:
            integrations_path = Path(__file__).parent / "data" / "integrations.json"

        self.integrations_path = integrations_path
        self._integrations: dict[str, Any] | None = None

    def _load_integrations(self) -> dict[str, Any]:
        """Load integrations configuration from JSON file"""
        try:
            with open(self.integrations_path, encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Integrations file not found: {self.integrations_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing integrations file: {e}")
            return {}

    @property
    def integrations(self) -> dict[str, Any]:
        """Get integrations config (lazy-loaded)"""
        if self._integrations is None:
            self._integrations = self._load_integrations()
        return self._integrations

    @property
    def integration_types(self) -> dict[str, Any]:
        return self.integrations.get("integration_types", {})

    @property
    def service_capabilities(self) -> dict[str, Any]:
        return self.integrations.get("service_capabilities", {})

    @property
    def integration_rules(self) -> dict[str, Any]:
        return self.integrations.get("integration_rules", {})

    @property
    def config_templates(self) -> dict[str, Any]:
        return self.integrations.get("config_templates", {})

    def detect_integrations(self, instances: list[dict]) -> dict[str, Any]:
        """
        Detect all possible integrations based on selected services

        Args:
            instances: List of instance configurations with app_id, instance_name, config

        Returns:
            Dictionary containing detected integrations, conflicts, and recommendations
        """
        result: dict[str, Any] = {
            "integrations": {},
            "conflicts": [],
            "warnings": [],
            "recommendations": [],
            "auto_add_services": [],
        }

        # Get list of selected service IDs
        selected_services = [inst["app_id"] for inst in instances]

        # Check mutual exclusivity
        conflicts = self.check_mutual_exclusivity(selected_services)
        result["conflicts"] = conflicts

        # Check dependencies
        deps = self.check_dependencies(selected_services, instances)
        result["warnings"].extend(deps["warnings"])
        result["auto_add_services"] = deps["auto_add"]

        # Detect available integrations
        for integration_type, type_config in self.integration_types.items():
            providers = [
                s for s in selected_services if s in type_config.get("providers", [])
            ]

            if providers:
                if integration_type == "reverse_proxy":
                    result["integrations"][integration_type] = self._detect_reverse_proxy(
                        providers[0], selected_services, instances
                    )
                elif integration_type == "oauth_provider":
                    result["integrations"][integration_type] = self._detect_oauth(
                        providers, selected_services, instances
                    )
                elif integration_type == "db_provider":
                    result["integrations"][integration_type] = self._detect_database(
                        providers, selected_services, instances
                    )
                elif integration_type == "mqtt_broker":
                    result["integrations"][integration_type] = self._detect_mqtt(
                        providers, selected_services, instances
                    )
                elif integration_type == "visualization":
                    result["integrations"][integration_type] = self._detect_visualization(
                        providers, selected_services, instances
                    )
                elif integration_type == "email_testing":
                    result["integrations"][integration_type] = self._detect_email(
                        providers, selected_services, instances
                    )

        # Get recommendations
        recommendations = self.get_recommendations(selected_services)
        result["recommendations"] = recommendations

        return result

    def check_mutual_exclusivity(self, selected_services: list[str]) -> list[dict]:
        """Check for mutually exclusive service conflicts"""
        conflicts = []

        exclusivity_rules = self.integration_rules.get("mutual_exclusivity", [])

        for rule in exclusivity_rules:
            group_services = rule["services"]
            selected_from_group = [s for s in selected_services if s in group_services]

            if len(selected_from_group) > 1:
                conflict = {
                    "group": rule["group"],
                    "services": selected_from_group,
                    "message": rule["message"],
                    "level": rule.get("level", "error"),
                }
                conflicts.append(conflict)

        return conflicts

    def check_dependencies(
        self, selected_services: list[str], instances: list[dict]
    ) -> dict:
        """Check for missing dependencies and requirements"""
        result: dict[str, list] = {"warnings": [], "auto_add": []}

        dependency_rules = self.integration_rules.get("dependencies", [])

        for rule in dependency_rules:
            service = rule["service"]

            if service not in selected_services:
                continue

            # Check hard requirements
            if "requires" in rule:
                req = rule["requires"]
                req_type = req.get("type")

                providers = self._find_providers(req_type, selected_services)

                if not providers:
                    if req.get("auto_add", False):
                        preferred = req.get("preferred")
                        if preferred:
                            result["auto_add"].append({
                                "service": preferred,
                                "reason": req.get("message", f"{service} requires {preferred}"),
                            })
                    else:
                        result["warnings"].append({
                            "service": service,
                            "message": req.get("message", f"{service} requires {req_type}"),
                            "level": "error",
                        })

            # Check recommendations
            if "recommends" in rule:
                rec = rule["recommends"]
                rec_type = rec.get("type")

                providers = self._find_providers(rec_type, selected_services)

                if not providers:
                    result["warnings"].append({
                        "service": service,
                        "message": rec.get("message", f"{service} recommends {rec_type}"),
                        "level": rec.get("level", "warning"),
                    })

        return result

    def get_recommendations(self, selected_services: list[str]) -> list[dict]:
        """Get recommendations for additional services based on current selection"""
        recommendations = []

        rec_rules = self.integration_rules.get("recommendations", [])

        for rule in rec_rules:
            if_selected = rule.get("if_selected", [])
            if_not_selected = rule.get("if_not_selected", [])

            if if_selected and all(s in selected_services for s in if_selected):
                if if_not_selected and all(s not in selected_services for s in if_not_selected):
                    recommendations.append({
                        "message": rule["message"],
                        "level": rule.get("level", "info"),
                        "suggest": rule.get("suggest", []),
                    })
                elif "suggest" in rule and not if_not_selected:
                    missing = [s for s in rule["suggest"] if s not in selected_services]
                    if missing:
                        recommendations.append({
                            "message": rule["message"],
                            "level": rule.get("level", "info"),
                            "suggest": missing,
                        })

            if "suggest_for" in rule:
                suggest_for = rule["suggest_for"]
                if if_selected and all(s in selected_services for s in if_selected):
                    applicable = [s for s in suggest_for if s in selected_services]
                    if applicable:
                        recommendations.append({
                            "message": rule["message"],
                            "level": rule.get("level", "info"),
                            "applies_to": applicable,
                        })

        return recommendations

    def _find_providers(self, integration_type: str, selected_services: list[str]) -> list[str]:
        """Find services that provide a specific integration type"""
        providers = []

        type_config = self.integration_types.get(integration_type, {})
        type_providers = type_config.get("providers", [])

        for service in selected_services:
            if service in type_providers:
                providers.append(service)

        return providers

    def _detect_reverse_proxy(
        self, provider: str, selected_services: list[str], instances: list[dict]
    ) -> dict:
        """Detect reverse proxy integrations"""
        integration: dict[str, Any] = {
            "provider": provider,
            "targets": [],
            "method": None,
            "config": {},
        }

        provider_caps = self.service_capabilities.get(provider, {})
        provider_integration = provider_caps.get("integrations", {}).get("reverse_proxy", {})
        integration["method"] = provider_integration.get("method", "docker_labels")

        type_config = self.integration_types.get("reverse_proxy", {})
        auto_targets = type_config.get("auto_configure_targets", [])

        for service_id in selected_services:
            if service_id == provider:
                continue

            if service_id in auto_targets:
                service_caps = self.service_capabilities.get(service_id, {})
                service_integration = service_caps.get("integrations", {}).get("reverse_proxy", {})

                if service_integration:
                    instance = next((i for i in instances if i["app_id"] == service_id), None)
                    if instance:
                        custom_name = instance.get("config", {}).get("name")
                        subdomain = custom_name or instance.get("instance_name") or service_id

                        target = {
                            "service_id": service_id,
                            "instance_name": instance.get("instance_name"),
                            "ports": service_integration.get("ports", []),
                            "default_subdomain": subdomain,
                            "health_check": service_integration.get("health_check"),
                        }
                        integration["targets"].append(target)

        return integration

    def _detect_oauth(
        self, providers: list[str], selected_services: list[str], instances: list[dict]
    ) -> dict:
        """Detect OAuth/SSO integrations"""
        integration: dict[str, Any] = {"providers": [], "clients": []}

        for provider_id in providers:
            # Build provider info dict (matching db_provider format)
            instance = next((i for i in instances if i["app_id"] == provider_id), None)
            if instance:
                integration["providers"].append({
                    "service_id": provider_id,
                    "instance_name": instance.get("instance_name"),
                    "config": instance.get("config", {}),
                })
            provider_caps = self.service_capabilities.get(provider_id, {})
            provider_integration = provider_caps.get("integrations", {}).get("oauth_provider", {})

            if not provider_integration:
                continue

            client_configs = provider_integration.get("client_configs", {})

            for service_id in selected_services:
                service_caps = self.service_capabilities.get(service_id, {})
                service_integration = service_caps.get("integrations", {}).get("oauth_provider", {})

                if service_integration and service_integration.get("type") == "client":
                    supports = service_integration.get("supports", [])

                    if provider_id in supports:
                        instance = next((i for i in instances if i["app_id"] == service_id), None)
                        if instance:
                            client = {
                                "service_id": service_id,
                                "instance_name": instance.get("instance_name"),
                                "provider": provider_id,
                                "env_vars": service_integration.get("env_vars", {}),
                                "client_config": client_configs.get(service_id, {}),
                            }
                            integration["clients"].append(client)

        return integration

    def _detect_database(
        self, providers: list[str], selected_services: list[str], instances: list[dict]
    ) -> dict:
        """Detect database integrations"""
        integration: dict[str, Any] = {"providers": [], "clients": []}

        for provider_id in providers:
            instance = next((i for i in instances if i["app_id"] == provider_id), None)
            if instance:
                provider_caps = self.service_capabilities.get(provider_id, {})
                provider_integration = provider_caps.get("integrations", {}).get("db_provider", {})

                provider_info = {
                    "service_id": provider_id,
                    "instance_name": instance.get("instance_name"),
                    "config": instance.get("config", {}),
                    "jdbc_url_template": provider_integration.get("jdbc_url_template"),
                    "default_port": provider_integration.get("default_port"),
                }
                integration["providers"].append(provider_info)

        for service_id in selected_services:
            service_caps = self.service_capabilities.get(service_id, {})
            service_integration = service_caps.get("integrations", {}).get("db_provider", {})

            if service_integration and service_integration.get("type") == "client":
                instance = next((i for i in instances if i["app_id"] == service_id), None)
                if instance:
                    client = {
                        "service_id": service_id,
                        "instance_name": instance.get("instance_name"),
                        "supports": service_integration.get("supports", []),
                        "auto_register": service_integration.get("auto_register", False),
                        "jdbc_drivers": service_integration.get("jdbc_drivers", {}),
                    }

                    compatible_providers = [
                        p for p in integration["providers"]
                        if p["service_id"] in client["supports"]
                    ]
                    client["matched_providers"] = compatible_providers

                    integration["clients"].append(client)

        return integration

    def _detect_mqtt(
        self, providers: list[str], selected_services: list[str], instances: list[dict]
    ) -> dict:
        """Detect MQTT broker integrations"""
        integration: dict[str, Any] = {"providers": [], "clients": []}

        for provider_id in providers:
            instance = next((i for i in instances if i["app_id"] == provider_id), None)
            if instance:
                provider_caps = self.service_capabilities.get(provider_id, {})
                provider_integration = provider_caps.get("integrations", {}).get("mqtt_broker", {})

                provider_info = {
                    "service_id": provider_id,
                    "instance_name": instance.get("instance_name"),
                    "mqtt_port": provider_integration.get("mqtt_port", 1883),
                    "ws_port": provider_integration.get("ws_port"),
                }
                integration["providers"].append(provider_info)

        for service_id in selected_services:
            service_caps = self.service_capabilities.get(service_id, {})
            service_integration = service_caps.get("integrations", {}).get("mqtt_broker", {})

            if service_integration and service_integration.get("type") == "client":
                instance = next((i for i in instances if i["app_id"] == service_id), None)
                if instance:
                    client = {
                        "service_id": service_id,
                        "instance_name": instance.get("instance_name"),
                        "supports": service_integration.get("supports", []),
                        "requires_module": service_integration.get("requires_module"),
                        "config_file": service_integration.get("config_file"),
                    }

                    compatible_providers = [
                        p for p in integration["providers"]
                        if p["service_id"] in client["supports"]
                    ]
                    client["matched_providers"] = compatible_providers

                    integration["clients"].append(client)

        return integration

    def _detect_visualization(
        self, providers: list[str], selected_services: list[str], instances: list[dict]
    ) -> dict:
        """Detect visualization (Grafana) datasource integrations"""
        integration: dict[str, Any] = {
            "provider": providers[0] if providers else None,
            "datasources": [],
        }

        if not integration["provider"]:
            return integration

        provider_caps = self.service_capabilities.get(integration["provider"], {})
        provider_integration = provider_caps.get("integrations", {}).get("visualization", {})
        datasource_types = provider_integration.get("datasource_types", {})

        for service_id in selected_services:
            if service_id in datasource_types:
                instance = next((i for i in instances if i["app_id"] == service_id), None)
                if instance:
                    datasource = {
                        "service_id": service_id,
                        "instance_name": instance.get("instance_name"),
                        "type": datasource_types[service_id],
                        "config": instance.get("config", {}),
                    }
                    integration["datasources"].append(datasource)

        return integration

    def _detect_email(
        self, providers: list[str], selected_services: list[str], instances: list[dict]
    ) -> dict:
        """Detect email testing (MailHog) integrations"""
        integration: dict[str, Any] = {
            "provider": providers[0] if providers else None,
            "clients": [],
        }

        if not integration["provider"]:
            return integration

        for service_id in selected_services:
            service_caps = self.service_capabilities.get(service_id, {})
            service_integration = service_caps.get("integrations", {}).get("email_testing", {})

            if service_integration and service_integration.get("type") == "client":
                instance = next((i for i in instances if i["app_id"] == service_id), None)
                if instance:
                    client = {
                        "service_id": service_id,
                        "instance_name": instance.get("instance_name"),
                        "env_vars": service_integration.get("env_vars", {}),
                    }
                    integration["clients"].append(client)

        return integration

    def generate_traefik_labels(
        self,
        service_name: str,
        subdomain: str,
        port: int,
        domain: str = "localhost",
        https: bool = False,
    ) -> list[str]:
        """Generate Traefik labels for a service"""
        template = self.config_templates.get(
            "traefik_https_label" if https else "traefik_label", []
        )

        labels = []
        for label_template in template:
            label = label_template.format(
                service_name=service_name, subdomain=subdomain, domain=domain, port=port
            )
            labels.append(label)

        return labels

    def get_integration_summary(self, detection_result: dict) -> str:
        """Generate a human-readable summary of detected integrations"""
        lines = ["# Integration Summary\n"]

        integrations = detection_result.get("integrations", {})

        if "reverse_proxy" in integrations:
            rp = integrations["reverse_proxy"]
            lines.append(f"## Reverse Proxy: {rp['provider']}")
            lines.append(f"Configured {len(rp['targets'])} services:")
            for target in rp["targets"]:
                lines.append(f"  - {target['instance_name']} -> {target['default_subdomain']}.localhost")
            lines.append("")

        if "oauth_provider" in integrations:
            oauth = integrations["oauth_provider"]
            provider_names = [p["service_id"] for p in oauth["providers"]]
            lines.append(f"## OAuth/SSO: {', '.join(provider_names)}")
            lines.append(f"Configured {len(oauth['clients'])} clients:")
            for client in oauth["clients"]:
                lines.append(f"  - {client['instance_name']} -> {client['provider']}")
            lines.append("")

        if "db_provider" in integrations:
            db = integrations["db_provider"]
            lines.append("## Databases")
            for provider in db["providers"]:
                lines.append(f"  Provider: {provider['instance_name']}")
            for client in db["clients"]:
                if client.get("auto_register"):
                    lines.append(f"  - Auto-registered in {client['instance_name']}")
            lines.append("")

        conflicts = detection_result.get("conflicts", [])
        if conflicts:
            lines.append("## Conflicts")
            for conflict in conflicts:
                lines.append(f"  - {conflict['message']}")
            lines.append("")

        warnings = detection_result.get("warnings", [])
        if warnings:
            lines.append("## Warnings")
            for warning in warnings:
                lines.append(f"  - {warning['message']}")
            lines.append("")

        return "\n".join(lines)


# Singleton instance
_engine: IntegrationEngine | None = None


def get_integration_engine() -> IntegrationEngine:
    """Get or create the integration engine singleton"""
    global _engine
    if _engine is None:
        _engine = IntegrationEngine()
    return _engine

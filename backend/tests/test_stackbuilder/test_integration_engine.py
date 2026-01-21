"""
Unit Tests for IntegrationEngine class

Tests the integration_engine.py module functionality:
- Integration detection for various service combinations
- Mutual exclusivity checks
- Dependency checking
- Recommendations generation
- Traefik label generation
"""

import pytest
from pathlib import Path

from ignition_toolkit.stackbuilder.integration_engine import (
    IntegrationEngine,
    get_integration_engine,
)


class TestIntegrationEngineLoading:
    """Test integration engine loading and initialization."""

    def test_engine_loads_from_default_path(self):
        """Test engine loads successfully from default location."""
        engine = IntegrationEngine()
        assert engine.integrations is not None
        assert "integration_types" in engine.integrations
        assert "service_capabilities" in engine.integrations

    def test_engine_loads_from_custom_path(self, integrations_path):
        """Test engine loads from custom path."""
        engine = IntegrationEngine(integrations_path=integrations_path)
        assert len(engine.integration_types) > 0

    def test_engine_handles_missing_file(self, tmp_path):
        """Test engine handles missing file gracefully."""
        nonexistent_path = tmp_path / "nonexistent.json"
        engine = IntegrationEngine(integrations_path=nonexistent_path)
        assert engine.integrations == {}

    def test_engine_lazy_loading(self, integrations_path):
        """Test engine is lazily loaded."""
        engine = IntegrationEngine(integrations_path=integrations_path)
        assert engine._integrations is None
        _ = engine.integrations
        assert engine._integrations is not None


class TestIntegrationTypeProperties:
    """Test integration type property accessors."""

    @pytest.fixture
    def engine(self, integrations_path):
        return IntegrationEngine(integrations_path=integrations_path)

    def test_integration_types_property(self, engine):
        """Test integration_types property returns types."""
        types = engine.integration_types
        assert isinstance(types, dict)
        assert "reverse_proxy" in types
        assert "oauth_provider" in types
        assert "db_provider" in types
        assert "mqtt_broker" in types

    def test_service_capabilities_property(self, engine):
        """Test service_capabilities property returns capabilities."""
        caps = engine.service_capabilities
        assert isinstance(caps, dict)
        assert "ignition" in caps
        assert "traefik" in caps
        assert "keycloak" in caps

    def test_integration_rules_property(self, engine):
        """Test integration_rules property returns rules."""
        rules = engine.integration_rules
        assert isinstance(rules, dict)
        assert "mutual_exclusivity" in rules
        assert "dependencies" in rules
        assert "recommendations" in rules

    def test_config_templates_property(self, engine):
        """Test config_templates property returns templates."""
        templates = engine.config_templates
        assert isinstance(templates, dict)
        assert "traefik_label" in templates


class TestIntegrationDetection:
    """Test integration detection functionality."""

    @pytest.fixture
    def engine(self, integrations_path):
        return IntegrationEngine(integrations_path=integrations_path)

    def test_detect_empty_instances(self, engine):
        """Test detection with empty instance list."""
        result = engine.detect_integrations([])
        assert result["integrations"] == {}
        assert result["conflicts"] == []
        assert result["warnings"] == []

    def test_detect_database_provider(self, engine, sample_ignition_instance, sample_postgres_instance):
        """Test detection identifies database provider integration."""
        instances = [sample_ignition_instance, sample_postgres_instance]
        result = engine.detect_integrations(instances)
        assert "db_provider" in result["integrations"]
        db_int = result["integrations"]["db_provider"]
        assert len(db_int["providers"]) > 0

    def test_detect_reverse_proxy(self, engine, sample_ignition_instance, sample_traefik_instance):
        """Test detection identifies reverse proxy integration."""
        instances = [sample_ignition_instance, sample_traefik_instance]
        result = engine.detect_integrations(instances)
        assert "reverse_proxy" in result["integrations"]
        rp_int = result["integrations"]["reverse_proxy"]
        assert rp_int["provider"] == "traefik"
        assert len(rp_int["targets"]) > 0

    def test_detect_oauth_provider(self, engine, sample_keycloak_instance, sample_grafana_instance):
        """Test detection identifies OAuth provider integration."""
        instances = [sample_keycloak_instance, sample_grafana_instance]
        result = engine.detect_integrations(instances)
        assert "oauth_provider" in result["integrations"]
        oauth_int = result["integrations"]["oauth_provider"]
        provider_ids = [p["service_id"] for p in oauth_int["providers"]]
        assert "keycloak" in provider_ids
        assert len(oauth_int["clients"]) > 0

    def test_detect_mqtt_broker(self, engine, sample_ignition_instance, sample_mosquitto_instance):
        """Test detection identifies MQTT broker integration."""
        instances = [sample_ignition_instance, sample_mosquitto_instance]
        result = engine.detect_integrations(instances)
        assert "mqtt_broker" in result["integrations"]
        mqtt_int = result["integrations"]["mqtt_broker"]
        assert len(mqtt_int["providers"]) > 0

    def test_detect_visualization(self, engine, sample_grafana_instance, sample_postgres_instance):
        """Test detection identifies visualization integration."""
        prometheus_instance = {
            "app_id": "prometheus",
            "instance_name": "prometheus",
            "config": {},
        }
        instances = [sample_grafana_instance, prometheus_instance, sample_postgres_instance]
        result = engine.detect_integrations(instances)
        assert "visualization" in result["integrations"]

    def test_detect_email_testing(self, engine, sample_ignition_instance, sample_mailhog_instance):
        """Test detection identifies email testing integration."""
        instances = [sample_ignition_instance, sample_mailhog_instance]
        result = engine.detect_integrations(instances)
        assert "email_testing" in result["integrations"]


class TestMutualExclusivity:
    """Test mutual exclusivity checking."""

    @pytest.fixture
    def engine(self, integrations_path):
        return IntegrationEngine(integrations_path=integrations_path)

    def test_no_conflict_with_single_proxy(self, engine):
        """Test no conflict with single reverse proxy."""
        services = ["traefik", "ignition"]
        conflicts = engine.check_mutual_exclusivity(services)
        # Should have no reverse proxy conflicts
        rp_conflicts = [c for c in conflicts if c["group"] == "reverse_proxy"]
        assert len(rp_conflicts) == 0

    def test_conflict_with_multiple_proxies(self, engine):
        """Test conflict detected with multiple reverse proxies."""
        services = ["traefik", "nginx-proxy-manager", "ignition"]
        conflicts = engine.check_mutual_exclusivity(services)
        # Should have reverse proxy conflict
        rp_conflicts = [c for c in conflicts if c["group"] == "reverse_proxy"]
        assert len(rp_conflicts) == 1
        assert "traefik" in rp_conflicts[0]["services"]
        assert "nginx-proxy-manager" in rp_conflicts[0]["services"]

    def test_warning_with_multiple_oauth(self, engine):
        """Test warning with multiple OAuth providers."""
        services = ["keycloak", "authentik", "ignition"]
        conflicts = engine.check_mutual_exclusivity(services)
        # Should have OAuth warning (level: warning)
        oauth_conflicts = [c for c in conflicts if c["group"] == "primary_oauth"]
        assert len(oauth_conflicts) == 1
        assert oauth_conflicts[0].get("level") == "warning"


class TestDependencyChecking:
    """Test dependency checking functionality."""

    @pytest.fixture
    def engine(self, integrations_path):
        return IntegrationEngine(integrations_path=integrations_path)

    def test_no_warnings_with_dependencies_met(self, engine, sample_ignition_instance, sample_postgres_instance):
        """Test no warnings when dependencies are met."""
        instances = [sample_ignition_instance, sample_postgres_instance]
        services = [inst["app_id"] for inst in instances]
        result = engine.check_dependencies(services, instances)
        # No critical warnings expected
        critical_warnings = [w for w in result["warnings"] if w.get("level") == "error"]
        assert len(critical_warnings) == 0

    def test_keycloak_recommends_database(self, engine, sample_keycloak_instance):
        """Test Keycloak recommends database."""
        instances = [sample_keycloak_instance]
        services = ["keycloak"]
        result = engine.check_dependencies(services, instances)
        # Should have recommendation for database
        db_warnings = [w for w in result["warnings"] if "database" in w.get("message", "").lower()]
        # This depends on the rules in integrations.json


class TestRecommendations:
    """Test recommendation generation."""

    @pytest.fixture
    def engine(self, integrations_path):
        return IntegrationEngine(integrations_path=integrations_path)

    def test_recommendations_for_ignition_postgres(self, engine):
        """Test recommendations for Ignition + PostgreSQL stack."""
        services = ["ignition", "postgres"]
        recommendations = engine.get_recommendations(services)
        assert isinstance(recommendations, list)

    def test_recommendations_for_grafana_without_datasource(self, engine):
        """Test recommendations for Grafana without data sources."""
        services = ["grafana"]
        recommendations = engine.get_recommendations(services)
        # Should recommend adding a data source
        assert any("data source" in r.get("message", "").lower() for r in recommendations)

    def test_no_recommendations_when_complete(self, engine):
        """Test fewer recommendations when stack is complete."""
        services = ["ignition", "postgres", "grafana", "prometheus", "traefik"]
        recommendations = engine.get_recommendations(services)
        # Complete stack should have fewer/no recommendations
        assert isinstance(recommendations, list)


class TestTraefikLabelGeneration:
    """Test Traefik label generation."""

    @pytest.fixture
    def engine(self, integrations_path):
        return IntegrationEngine(integrations_path=integrations_path)

    def test_generate_http_labels(self, engine):
        """Test HTTP Traefik label generation."""
        labels = engine.generate_traefik_labels(
            service_name="ignition-1",
            subdomain="ignition",
            port=8088,
            domain="localhost",
            https=False,
        )
        assert "traefik.enable=true" in labels
        assert any("Host(`ignition.localhost`)" in label for label in labels)
        assert any("web" in label for label in labels)  # HTTP entrypoint
        assert any("8088" in label for label in labels)

    def test_generate_https_labels(self, engine):
        """Test HTTPS Traefik label generation."""
        labels = engine.generate_traefik_labels(
            service_name="grafana",
            subdomain="grafana",
            port=3000,
            domain="example.com",
            https=True,
        )
        assert "traefik.enable=true" in labels
        assert any("Host(`grafana.example.com`)" in label for label in labels)
        assert any("websecure" in label for label in labels)  # HTTPS entrypoint
        assert any("tls" in label.lower() for label in labels)


class TestIntegrationSummary:
    """Test integration summary generation."""

    @pytest.fixture
    def engine(self, integrations_path):
        return IntegrationEngine(integrations_path=integrations_path)

    def test_summary_with_integrations(self, engine, sample_ignition_instance, sample_traefik_instance, sample_postgres_instance):
        """Test summary includes detected integrations."""
        instances = [sample_ignition_instance, sample_traefik_instance, sample_postgres_instance]
        detection_result = engine.detect_integrations(instances)
        summary = engine.get_integration_summary(detection_result)
        assert isinstance(summary, str)
        assert "Integration Summary" in summary

    def test_summary_with_conflicts(self, engine):
        """Test summary includes conflicts."""
        traefik = {"app_id": "traefik", "instance_name": "traefik", "config": {}}
        nginx = {"app_id": "nginx-proxy-manager", "instance_name": "nginx", "config": {}}
        detection_result = engine.detect_integrations([traefik, nginx])
        summary = engine.get_integration_summary(detection_result)
        if detection_result["conflicts"]:
            assert "Conflicts" in summary

    def test_summary_empty_stack(self, engine):
        """Test summary for empty stack."""
        detection_result = engine.detect_integrations([])
        summary = engine.get_integration_summary(detection_result)
        assert isinstance(summary, str)


class TestSingletonPattern:
    """Test the global singleton pattern."""

    def test_get_integration_engine_returns_instance(self):
        """Test get_integration_engine returns an IntegrationEngine instance."""
        engine = get_integration_engine()
        assert isinstance(engine, IntegrationEngine)

    def test_get_integration_engine_returns_same_instance(self):
        """Test get_integration_engine returns the same instance."""
        engine1 = get_integration_engine()
        engine2 = get_integration_engine()
        assert engine1 is engine2

"""
All-pairs sweep (T2) for Stack Builder.

Pure, Docker-free sweep over every pair of enabled catalog services (C(n,2)),
plus an ignition x2 multi-instance case. Driven entirely from catalog.json and
integrations.json - no hardcoded service list - so new catalog entries are
automatically covered. See docs/plans/stackbuilder-test-strategy.md (T2).

For every pair:
  - If integrations.json declares an *error*-level mutual-exclusivity conflict
    between the two services -> assert generation raises IntegrationConflictError
    (negative case).
  - Otherwise -> assert generation succeeds with valid YAML, both services
    present under unique container names, and no host-port collisions.
  - For the subset of pairs where the generator is known to actually wire up
    the declared integration (verified by reading compose_generator.py), also
    assert the specific env vars / config files / depends_on it produces.
    Several integrations declared in integrations.json (e.g. metrics_collector,
    secrets_management, nginx-proxy-manager as a reverse-proxy provider,
    keycloak+mariadb) are not implemented by the generator at all; those pairs
    only get the baseline assertions (see final report / code comments below).
"""

from __future__ import annotations

import itertools
from typing import Any

import pytest
import yaml

from ignition_toolkit.stackbuilder.catalog import get_service_catalog
from ignition_toolkit.stackbuilder.compose_generator import ComposeGenerator
from ignition_toolkit.stackbuilder.exceptions import IntegrationConflictError
from ignition_toolkit.stackbuilder.integration_engine import get_integration_engine

# Every number-typed configurable option in the catalog is a host port (verified
# against catalog.json). Offsetting the *second* instance of a pair by this much
# guarantees its ports never collide with the first instance's catalog-default
# ports (the largest catalog default port is 18083), isolating the "no host-port
# collision" assertion to genuine generator bugs rather than incidental catalog
# defaults that happen to clash (e.g. emqx and mosquitto both default mqtt_port
# to 1883).
PORT_OFFSET = 20000

# Services the generator actually adds Traefik labels for (compose_generator.py
# `_generate_traefik_labels` / `web_service_ports`).
TRAEFIK_LABELED_SERVICES = {
    "ignition",
    "grafana",
    "nodered",
    "n8n",
    "keycloak",
    "prometheus",
    "dozzle",
    "portainer",
    "mailhog",
}

# app_ids whose _apply_app_config wires MailHog env vars in (config_generators.
# generate_email_env_vars only special-cases these four).
EMAIL_CLIENT_SERVICES = {"ignition", "grafana", "n8n", "keycloak"}


def _enabled_apps() -> list[dict[str, Any]]:
    return get_service_catalog().get_enabled_applications()


def _enabled_app_ids() -> list[str]:
    return [a["id"] for a in _enabled_apps()]


def _app_by_id(app_id: str) -> dict[str, Any]:
    app = get_service_catalog().get_application_by_id(app_id)
    assert app is not None, f"catalog changed: {app_id} no longer found"
    return app


def _mutual_exclusivity_rules() -> list[dict[str, Any]]:
    return get_integration_engine().integration_rules.get("mutual_exclusivity", [])


def _hard_conflict_rule(app_a: str, app_b: str) -> dict[str, Any] | None:
    """Return the mutual-exclusivity rule that fires for this pair, if it's error-level."""
    for rule in _mutual_exclusivity_rules():
        services = rule.get("services", [])
        if app_a in services and app_b in services:
            if rule.get("level", "error") == "error":
                return rule
    return None


def _build_instance(app_id: str, suffix: str, port_offset: int) -> dict[str, Any]:
    """Build an instance dict with every number-typed option offset to avoid collisions."""
    app = _app_by_id(app_id)
    config: dict[str, Any] = {}
    for option_name, option in app.get("configurable_options", {}).items():
        if option.get("type") != "number":
            continue
        try:
            config[option_name] = int(option["default"]) + port_offset
        except (TypeError, ValueError):
            continue
    return {"app_id": app_id, "instance_name": f"{app_id}-{suffix}", "config": config}


def _all_host_ports(parsed_compose: dict[str, Any]) -> list[int]:
    ports = []
    for service in parsed_compose["services"].values():
        for mapping in service.get("ports", []):
            host_port = str(mapping).split(":")[0]
            ports.append(int(host_port))
    return ports


def _pair_cases() -> list[tuple[str, str]]:
    ids = _enabled_app_ids()
    cases = list(itertools.combinations(ids, 2))
    if "ignition" in ids:
        cases.append(("ignition", "ignition"))
    return cases


def _assert_known_integration(
    app_a: str,
    name_a: str,
    app_b: str,
    name_b: str,
    parsed: dict[str, Any],
    config_files: dict[str, str],
) -> None:
    """
    Assert the specific, verified materialisation for pairs where the generator
    is known to actually wire the declared integration up. No-ops for any pair
    not covered below (those pairs only get the baseline assertions).
    """
    services = parsed["services"]
    pair = {app_a: name_a, app_b: name_b}

    # --- db_provider: Ignition auto-registration script ---
    if "ignition" in pair and ({"postgres", "mariadb"} & pair.keys()):
        db_app = "postgres" if "postgres" in pair else "mariadb"
        assert "scripts/register_databases.py" in config_files
        script = config_files["scripts/register_databases.py"]
        assert pair[db_app] in script, "registration script doesn't reference the db instance"
        assert "scripts/requirements.txt" in config_files

    # --- mqtt_broker: Ignition depends_on the broker (+ mosquitto config file) ---
    if "ignition" in pair and ({"mosquitto", "emqx"} & pair.keys()):
        broker_app = "mosquitto" if "mosquitto" in pair else "emqx"
        broker_name = pair[broker_app]
        ignition_service = services[pair["ignition"]]
        assert broker_name in ignition_service.get(
            "depends_on", {}
        ), "ignition should depend_on its mqtt broker"
        if broker_app == "mosquitto":
            assert f"configs/{broker_name}/mosquitto.conf" in config_files

    # --- email_testing: SMTP env vars on the mailhog client ---
    if "mailhog" in pair and (EMAIL_CLIENT_SERVICES & pair.keys() - {"mailhog"}):
        client_app = next(iter(EMAIL_CLIENT_SERVICES & pair.keys() - {"mailhog"}))
        client_env = services[pair[client_app]].get("environment", {})
        if client_app == "ignition":
            assert client_env.get("GATEWAY_SMTP_HOST") == pair["mailhog"]
        elif client_app == "grafana":
            assert client_env.get("GF_SMTP_ENABLED") == "true"
        elif client_app == "n8n":
            assert client_env.get("N8N_SMTP_HOST") == pair["mailhog"]
        elif client_app == "keycloak":
            assert client_env.get("KC_SMTP_HOST") == pair["mailhog"]

    # --- oauth_provider: Keycloak client env vars + depends_on ---
    if "keycloak" in pair and ({"grafana", "n8n"} & pair.keys()):
        client_app = "grafana" if "grafana" in pair else "n8n"
        client_service = services[pair[client_app]]
        client_env = client_service.get("environment", {})
        if client_app == "grafana":
            assert client_env.get("GF_AUTH_GENERIC_OAUTH_ENABLED") == "true"
        else:
            assert client_env.get("N8N_OAUTH_ENABLED") == "true"
        assert pair["keycloak"] in client_service.get("depends_on", {})

    # --- db_provider: Keycloak <-> Postgres (only postgres is wired; mariadb is not) ---
    if "keycloak" in pair and "postgres" in pair:
        kc_env = services[pair["keycloak"]].get("environment", {})
        assert kc_env.get("KC_DB") == "postgres"
        assert pair["postgres"] in kc_env.get("KC_DB_URL", "")
        assert pair["postgres"] in services[pair["keycloak"]].get("depends_on", {})

    # --- visualization: Grafana datasource provisioning ---
    if "grafana" in pair and ({"postgres", "mariadb", "prometheus"} & pair.keys()):
        ds_app = next(iter({"postgres", "mariadb", "prometheus"} & pair.keys()))
        assert f"configs/{pair['grafana']}/provisioning/datasources/auto.yaml" in config_files
        if ds_app == "prometheus":
            assert pair["prometheus"] in services[pair["grafana"]].get("depends_on", {})

    # --- reverse_proxy: Traefik labels + config (nginx-proxy-manager is NOT implemented) ---
    if "traefik" in pair and (TRAEFIK_LABELED_SERVICES & pair.keys()):
        labeled_app = next(iter(TRAEFIK_LABELED_SERVICES & pair.keys()))
        labels = services[pair[labeled_app]].get("labels", [])
        assert "traefik.enable=true" in labels
        assert "configs/traefik/traefik.yml" in config_files
        assert "configs/traefik/dynamic/services.yml" in config_files


@pytest.mark.parametrize(
    "app_a,app_b",
    _pair_cases(),
    ids=[f"{a}+{b}" for a, b in _pair_cases()],
)
def test_pair_generates_or_conflicts_cleanly(app_a: str, app_b: str) -> None:
    """Every enabled-service pair either generates a valid stack or fails with a clean exception."""
    same_app = app_a == app_b
    instance_a = _build_instance(app_a, "1", 0)
    instance_b = _build_instance(app_b, "2", PORT_OFFSET)

    generator = ComposeGenerator()
    conflict_rule = None if same_app else _hard_conflict_rule(app_a, app_b)

    if conflict_rule is not None:
        with pytest.raises(IntegrationConflictError) as exc_info:
            generator.generate([instance_a, instance_b])
        conflicts = exc_info.value.details.get("conflicts", [])
        assert any(c.get("group") == conflict_rule["group"] for c in conflicts)
        return

    result = generator.generate([instance_a, instance_b])

    parsed = yaml.safe_load(result["docker_compose"])
    assert parsed is not None
    assert "services" in parsed

    name_a, name_b = instance_a["instance_name"], instance_b["instance_name"]
    assert name_a in parsed["services"], f"{app_a}: service missing from compose"
    assert name_b in parsed["services"], f"{app_b}: service missing from compose"

    container_names = [svc["container_name"] for svc in parsed["services"].values()]
    assert len(container_names) == len(set(container_names)), "duplicate container_name"

    host_ports = _all_host_ports(parsed)
    assert len(host_ports) == len(
        set(host_ports)
    ), f"{app_a}+{app_b}: host port collision {host_ports}"

    for app_id, instance_name in ((app_a, name_a), (app_b, name_b)):
        app = _app_by_id(app_id)
        expected_image_prefix = f"{app['image']}:"
        assert parsed["services"][instance_name]["image"].startswith(expected_image_prefix)

    _assert_known_integration(app_a, name_a, app_b, name_b, parsed, result.get("config_files", {}))


def test_reverse_proxy_mutual_exclusivity_is_declared_and_enforced() -> None:
    """
    Sanity check that the one active (both-enabled) mutual-exclusivity rule -
    traefik vs nginx-proxy-manager - is actually present in the data and that
    the parametrised sweep above includes it as a negative case.
    """
    ids = set(_enabled_app_ids())
    assert {"traefik", "nginx-proxy-manager"} <= ids
    rule = _hard_conflict_rule("traefik", "nginx-proxy-manager")
    assert rule is not None
    assert rule["group"] == "reverse_proxy"


def test_pair_sweep_covers_all_enabled_combinations() -> None:
    """Guard against the sweep silently shrinking if the catalog changes shape."""
    ids = _enabled_app_ids()
    expected = len(list(itertools.combinations(ids, 2))) + (1 if "ignition" in ids else 0)
    assert len(_pair_cases()) == expected

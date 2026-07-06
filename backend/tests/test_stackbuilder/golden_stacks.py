"""
Shared golden-stack definitions for Stack Builder T3/T4 tests.

Not a test module itself (pytest won't collect it - no `test_` prefix); it is
imported by both:
  - test_goldens.py (T4): byte-exact snapshot comparison against goldens/<id>/
  - test_compose_spec.py (T3): `docker compose config` validation of the same
    curated stacks

See docs/plans/stackbuilder-test-strategy.md for the overall strategy and
goldens/README.md for the secret-normalisation rationale below.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any

from ignition_toolkit.stackbuilder.compose_generator import ComposeGenerator

# --- Golden stack definitions ----------------------------------------------


def _instance(
    app_id: str, instance_name: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build one Stack Builder instance dict."""
    return {"app_id": app_id, "instance_name": instance_name, "config": config or {}}


@dataclass(frozen=True)
class GoldenStack:
    """One curated, realistic stack used for golden-file snapshotting."""

    id: str
    description: str
    instances: list[dict[str, Any]] = field(default_factory=list)


GOLDEN_STACKS: list[GoldenStack] = [
    GoldenStack(
        id="ignition_postgres",
        description="Minimal historian pairing: Ignition + PostgreSQL.",
        instances=[_instance("ignition", "ignition"), _instance("postgres", "postgres")],
    ),
    GoldenStack(
        id="ignition_postgres_keycloak_traefik",
        description=(
            "Ignition behind Traefik with Postgres storage and Keycloak present as "
            "an SSO provider (no OAuth client configured, so no generated secrets)."
        ),
        instances=[
            _instance("ignition", "ignition"),
            _instance("postgres", "postgres"),
            _instance("keycloak", "keycloak"),
            _instance("traefik", "traefik"),
        ],
    ),
    GoldenStack(
        id="ignition_emqx_nodered",
        description="MQTT-centric IIoT stack: Ignition + EMQX broker + Node-RED.",
        instances=[
            _instance("ignition", "ignition"),
            _instance("emqx", "emqx"),
            _instance("nodered", "nodered"),
        ],
    ),
    GoldenStack(
        id="ignition_prometheus_grafana_dozzle",
        description=(
            "Monitoring stack: Ignition + Prometheus + Grafana "
            "(datasource auto-provisioned) + Dozzle."
        ),
        instances=[
            _instance("ignition", "ignition"),
            _instance("prometheus", "prometheus"),
            _instance("grafana", "grafana"),
            _instance("dozzle", "dozzle"),
        ],
    ),
    GoldenStack(
        id="ignition_x2_mariadb",
        description="Multi-instance Ignition (two gateways) sharing a MariaDB database.",
        instances=[
            _instance("ignition", "ignition-primary"),
            _instance("ignition", "ignition-secondary", {"http_port": 8089, "https_port": 8044}),
            _instance("mariadb", "mariadb"),
        ],
    ),
    GoldenStack(
        id="oauth_email_stack",
        description=(
            "Keycloak OAuth provider wired to Grafana, Postgres as both a Keycloak "
            "datastore and a Grafana datasource, and MailHog for SMTP testing. "
            "Exercises the generated-client-secret normalisation (see goldens/README.md)."
        ),
        instances=[
            _instance("keycloak", "keycloak"),
            _instance("grafana", "grafana"),
            _instance("postgres", "postgres"),
            _instance("mailhog", "mailhog"),
        ],
    ),
    GoldenStack(
        id="full_mixed_stack",
        description=(
            "Larger, kitchen-sink stack combining reverse proxy, OAuth, database, "
            "MQTT, monitoring, and email integrations in a single generation."
        ),
        instances=[
            _instance("ignition", "ignition"),
            _instance("postgres", "postgres"),
            _instance("keycloak", "keycloak"),
            _instance("traefik", "traefik"),
            _instance("grafana", "grafana"),
            _instance("prometheus", "prometheus"),
            _instance("mosquitto", "mosquitto"),
            _instance("nodered", "nodered"),
            _instance("mailhog", "mailhog"),
        ],
    ),
]


def generate_stack(stack: GoldenStack) -> dict[str, Any]:
    """Run the real generator for one golden stack (pure, no docker)."""
    return ComposeGenerator().generate(copy.deepcopy(stack.instances))


# --- Secret normalisation ---------------------------------------------------
#
# ComposeGenerator wires Keycloak OAuth clients (Grafana/n8n/Portainer/Ignition)
# with a fresh `secrets.token_urlsafe(32)` client secret on every call
# (keycloak_generator.generate_client_secret). The same value is threaded
# through to the client service's compose environment (e.g.
# GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET) and to the Keycloak realm-import JSON
# (`clients[*].secret`), so a single generation is internally consistent but
# never byte-identical across two runs. Both locations are normalised to a
# fixed placeholder before snapshotting/comparing. Verified nowhere else in
# the generator produces nondeterministic output with default settings
# (admin/db passwords are static catalog defaults; the Mosquitto password
# file's PBKDF2 salt is also nondeterministic but is only generated when MQTT
# credentials are explicitly configured - none of the golden stacks do, so
# that path is deliberately not exercised here).

SECRET_PLACEHOLDER = "NORMALIZED_SECRET"

# Env var keys in the generated docker-compose.yml whose value is a randomly
# generated OAuth client secret (config_generators.generate_oauth_env_vars).
_SECRET_ENV_KEYS = ("GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET", "N8N_OAUTH_CLIENT_SECRET")
_SECRET_ENV_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<key>" + "|".join(_SECRET_ENV_KEYS) + r"):[ \t]*.*$",
    re.MULTILINE,
)


def _normalize_compose_yaml(compose_yaml: str) -> str:
    return _SECRET_ENV_RE.sub(
        lambda m: f"{m.group('indent')}{m.group('key')}: {SECRET_PLACEHOLDER}", compose_yaml
    )


def _normalize_realm_json(raw_json: str) -> str:
    """Blank out `clients[*].secret` in a Keycloak realm-import JSON file."""
    realm = json.loads(raw_json)
    for client in realm.get("clients", []):
        if "secret" in client:
            client["secret"] = SECRET_PLACEHOLDER
    return json.dumps(realm, indent=2)


def normalize_artifacts(result: dict[str, Any]) -> dict[str, Any]:
    """
    Return a copy of a ComposeGenerator.generate() result with all known
    non-deterministic secrets replaced by a fixed placeholder, so it can be
    snapshotted/compared byte-exactly. See the module-level note above.
    """
    normalized = dict(result)
    normalized["docker_compose"] = _normalize_compose_yaml(result["docker_compose"])

    config_files = dict(result.get("config_files", {}))
    for path, content in config_files.items():
        if path.startswith("configs/keycloak/import/realm-") and path.endswith(".json"):
            config_files[path] = _normalize_realm_json(content)
    normalized["config_files"] = config_files

    return normalized

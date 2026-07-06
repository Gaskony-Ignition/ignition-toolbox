"""
Single-service sweep (T1) for Stack Builder.

Pure, Docker-free sweep over every enabled catalog service: generate it alone
with default config, then once per configurable option set to a non-default
value (~140 generations total). Confirms the generator never produces invalid
output as options vary. See docs/plans/stackbuilder-test-strategy.md (T1).

Assertions per generation:
  - docker-compose YAML parses
  - the instance's service is present
  - the service's image:tag matches the catalog (respecting a custom version)
  - every ${VAR} referenced in the compose output exists in the generated .env
"""

from __future__ import annotations

import re
from typing import Any

import pytest
import yaml

from ignition_toolkit.stackbuilder.catalog import get_service_catalog
from ignition_toolkit.stackbuilder.compose_generator import ComposeGenerator

VAR_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _enabled_apps() -> list[dict[str, Any]]:
    """All enabled catalog applications, loaded once at collection time."""
    return get_service_catalog().get_enabled_applications()


def _option_value(value: Any) -> Any:
    """Unwrap a catalog option entry that may be `{"value": ..., "label": ...}` or a bare value."""
    return value["value"] if isinstance(value, dict) else value


def _non_default_value(app: dict[str, Any], option_name: str, option: dict[str, Any]) -> Any:
    """
    Pick a value different from the option's default for a sweep case.

    Returns a sentinel (`_NO_ALTERNATIVE`) when no distinct value can be derived
    (e.g. a select with no alternatives listed), so the caller can skip it.
    """
    opt_type = option.get("type")
    default = option.get("default")

    if option_name == "version":
        for candidate in app.get("available_versions", []):
            if candidate != default:
                return candidate
        return _NO_ALTERNATIVE

    if opt_type == "select":
        for opt in option.get("options") or []:
            candidate = _option_value(opt)
            if candidate != default:
                return candidate
        return _NO_ALTERNATIVE

    if opt_type == "multiselect":
        all_values = [_option_value(opt) for opt in option.get("options") or []]
        default_list = default or []
        alternative = [v for v in all_values if v not in default_list]
        if alternative:
            return alternative
        if default_list:
            return []
        return _NO_ALTERNATIVE

    if opt_type == "number":
        try:
            return int(default) + 1
        except (TypeError, ValueError):
            return _NO_ALTERNATIVE

    if opt_type == "checkbox":
        return not bool(default)

    if opt_type in ("text", "password", "textarea"):
        return f"{default}-alt" if default else "alt-value"

    return _NO_ALTERNATIVE


_NO_ALTERNATIVE = object()


def _build_option_sweep_cases() -> list[tuple[dict[str, Any], str, Any]]:
    cases = []
    for app in _enabled_apps():
        for option_name, option in app.get("configurable_options", {}).items():
            value = _non_default_value(app, option_name, option)
            if value is _NO_ALTERNATIVE:
                continue
            cases.append((app, option_name, value))
    return cases


def _generate_single(app: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    generator = ComposeGenerator()
    instance = {
        "app_id": app["id"],
        "instance_name": f"{app['id']}-under-test",
        "config": config,
    }
    return generator.generate([instance]), instance


def _assert_clean_generation(app: dict[str, Any], config: dict[str, Any]) -> None:
    result, instance = _generate_single(app, config)

    parsed = yaml.safe_load(result["docker_compose"])
    assert parsed is not None, f"{app['id']}: docker-compose YAML failed to parse"
    assert "services" in parsed

    service_name = instance["instance_name"]
    assert service_name in parsed["services"], f"{app['id']}: service missing from compose output"
    service = parsed["services"][service_name]

    expected_version = config.get("version", app.get("default_version", "latest"))
    expected_image = f"{app['image']}:{expected_version}"
    assert (
        service["image"] == expected_image
    ), f"{app['id']}: image {service['image']!r} does not match catalog {expected_image!r}"

    env_names = {
        line.split("=", 1)[0]
        for line in result["env"].splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    referenced_vars = set(VAR_REF_RE.findall(result["docker_compose"]))
    missing = referenced_vars - env_names
    assert (
        not missing
    ), f"{app['id']}: ${{VAR}} referenced in compose but not defined in .env: {sorted(missing)}"


@pytest.mark.parametrize("app", _enabled_apps(), ids=lambda a: a["id"])
def test_default_config_generates_cleanly(app: dict[str, Any]) -> None:
    """Every enabled service generates a valid stack alone, using pure catalog defaults."""
    _assert_clean_generation(app, config={})


_OPTION_SWEEP_CASES = _build_option_sweep_cases()


@pytest.mark.parametrize(
    "app,option_name,value",
    _OPTION_SWEEP_CASES,
    ids=[f"{app['id']}-{option_name}" for app, option_name, _ in _OPTION_SWEEP_CASES],
)
def test_option_sweep_generates_cleanly(app: dict[str, Any], option_name: str, value: Any) -> None:
    """Every configurable option, set once to a non-default value, still generates cleanly."""
    _assert_clean_generation(app, config={option_name: value})


def test_sweep_covers_every_enabled_service() -> None:
    """Guard against the sweep silently shrinking if the catalog changes shape."""
    apps = _enabled_apps()
    assert len(apps) >= 1
    swept_ids = {app["id"] for app in apps}
    option_swept_ids = {app["id"] for app, _, _ in _OPTION_SWEEP_CASES}
    # Every enabled app has at least a "version" option, so it should appear here too.
    assert option_swept_ids <= swept_ids

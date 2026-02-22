"""
Tests for YAML playbook schema validation.

Loads every YAML file under backend/playbooks/ and validates:
- Required top-level fields: name, version, description, domain, steps
- domain is one of: gateway, designer, perspective
- Every step type is a known step type from the registry
- Reports ALL failures, not just the first one
"""

from pathlib import Path
import pytest
import yaml

PLAYBOOKS_DIR = Path(__file__).parent.parent.parent / "playbooks"
REQUIRED_FIELDS = {"name", "version", "description", "domain", "steps"}
VALID_DOMAINS = {"gateway", "designer", "perspective"}


def get_known_step_types() -> set[str]:
    """Return all step type string values from the step type registry."""
    from ignition_toolkit.playbook.step_type_registry import get_all_definitions

    return {defn.type_value for defn in get_all_definitions()}


def load_all_playbooks() -> list[tuple[Path, dict]]:
    """Load all YAML files under backend/playbooks/."""
    playbooks = []
    for yaml_file in sorted(PLAYBOOKS_DIR.rglob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        playbooks.append((yaml_file, data))
    return playbooks


class TestYamlSchema:
    def test_playbooks_directory_exists(self):
        """The playbooks directory exists and contains YAML files."""
        assert PLAYBOOKS_DIR.is_dir(), f"Playbooks directory not found: {PLAYBOOKS_DIR}"
        yaml_files = list(PLAYBOOKS_DIR.rglob("*.yaml"))
        assert yaml_files, "No YAML files found in playbooks directory"

    def test_all_playbooks_have_required_fields(self):
        """Every playbook YAML has name, version, description, domain, and steps."""
        failures = []
        for yaml_file, data in load_all_playbooks():
            missing = REQUIRED_FIELDS - set(data.keys() if isinstance(data, dict) else [])
            if missing:
                failures.append(f"{yaml_file.name}: missing fields {sorted(missing)}")

        assert not failures, (
            f"{len(failures)} playbook(s) with missing required fields:\n"
            + "\n".join(f"  {f}" for f in failures)
        )

    def test_all_playbooks_have_valid_domain(self):
        """Every playbook YAML has a domain value in {gateway, designer, perspective}."""
        failures = []
        for yaml_file, data in load_all_playbooks():
            if not isinstance(data, dict):
                continue
            domain = data.get("domain")
            if domain not in VALID_DOMAINS:
                failures.append(
                    f"{yaml_file.name}: invalid domain '{domain}' "
                    f"(must be one of {sorted(VALID_DOMAINS)})"
                )

        assert not failures, (
            f"{len(failures)} playbook(s) with invalid domain:\n"
            + "\n".join(f"  {f}" for f in failures)
        )

    def test_all_playbooks_have_valid_step_types(self):
        """Every step in every playbook uses a type string known to the registry."""
        known_types = get_known_step_types()
        failures = []
        for yaml_file, data in load_all_playbooks():
            if not isinstance(data, dict):
                continue
            steps = data.get("steps") or []
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                step_type = step.get("type")
                if step_type and step_type not in known_types:
                    failures.append(
                        f"{yaml_file.name}: step[{i}] (id={step.get('id', '?')!r}) "
                        f"unknown type '{step_type}'"
                    )

        assert not failures, (
            f"{len(failures)} step(s) with unknown type:\n"
            + "\n".join(f"  {f}" for f in failures)
        )

    def test_all_steps_have_id_and_type(self):
        """Every step in every playbook has both 'id' and 'type' fields."""
        failures = []
        for yaml_file, data in load_all_playbooks():
            if not isinstance(data, dict):
                continue
            steps = data.get("steps") or []
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    failures.append(f"{yaml_file.name}: steps[{i}] is not a mapping")
                    continue
                if "id" not in step:
                    failures.append(f"{yaml_file.name}: steps[{i}] missing 'id'")
                if "type" not in step:
                    failures.append(f"{yaml_file.name}: steps[{i}] missing 'type'")

        assert not failures, (
            f"{len(failures)} step(s) missing required fields:\n"
            + "\n".join(f"  {f}" for f in failures)
        )

#!/usr/bin/env python3
"""
Standalone playbook schema validation script.

Validates all YAML files under backend/playbooks/:
  - Required top-level fields: name, version, description, domain, steps
  - Valid domain values: gateway, designer, perspective
  - Valid step type strings (from the step type registry)

Exit code 0 if all valid, 1 if any issues found.

Usage:
    python scripts/validate-playbooks.py
    python scripts/validate-playbooks.py --playbooks-dir /custom/path
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Ensure the backend package is importable when run from the project root
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

REQUIRED_FIELDS = {"name", "version", "description", "domain", "steps"}
VALID_DOMAINS = {"gateway", "designer", "perspective"}


def get_known_step_types() -> set[str]:
    """Load known step types from the registry. Returns empty set on import failure."""
    try:
        from ignition_toolkit.playbook.step_type_registry import get_all_definitions

        return {defn.type_value for defn in get_all_definitions()}
    except ImportError as e:
        print(f"WARNING: Could not import step type registry: {e}")
        print("         Step type validation will be skipped.")
        return set()


def validate_playbooks(playbooks_dir: Path) -> list[str]:
    """
    Validate all YAML files under playbooks_dir.

    Returns a list of error strings — empty list means all files are valid.
    Reports ALL failures, not just the first one found.
    """
    errors: list[str] = []
    known_types = get_known_step_types()
    validate_step_types = bool(known_types)

    yaml_files = sorted(playbooks_dir.rglob("*.yaml"))
    if not yaml_files:
        print(f"No YAML files found under {playbooks_dir}")
        return []

    for yaml_file in yaml_files:
        rel_path = yaml_file.relative_to(playbooks_dir)

        # Parse YAML
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"[{rel_path}] YAML parse error: {e}")
            continue

        if not isinstance(data, dict):
            errors.append(
                f"[{rel_path}] Expected a YAML mapping at the top level, "
                f"got {type(data).__name__}"
            )
            continue

        # Required top-level fields
        missing = REQUIRED_FIELDS - set(data.keys())
        for field in sorted(missing):
            errors.append(f"[{rel_path}] Missing required field: '{field}'")

        # Valid domain
        domain = data.get("domain")
        if domain not in VALID_DOMAINS:
            errors.append(
                f"[{rel_path}] Invalid domain '{domain}' "
                f"— must be one of {sorted(VALID_DOMAINS)}"
            )

        # Valid step types
        if validate_step_types:
            steps = data.get("steps") or []
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    errors.append(f"[{rel_path}] steps[{i}] is not a mapping")
                    continue
                step_type = step.get("type")
                if step_type and step_type not in known_types:
                    errors.append(
                        f"[{rel_path}] steps[{i}] (id={step.get('id', '?')!r}): "
                        f"unknown step type '{step_type}'"
                    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Ignition Toolbox playbook YAML files"
    )
    parser.add_argument(
        "--playbooks-dir",
        type=Path,
        default=BACKEND_DIR / "playbooks",
        help="Directory containing playbook YAML files (default: backend/playbooks)",
    )
    args = parser.parse_args()

    playbooks_dir: Path = args.playbooks_dir
    if not playbooks_dir.is_dir():
        print(f"ERROR: Playbooks directory not found: {playbooks_dir}")
        return 1

    print(f"Validating playbooks in: {playbooks_dir}")
    errors = validate_playbooks(playbooks_dir)

    if errors:
        print(f"\nFAILED: {len(errors)} validation error(s) found:\n")
        for error in errors:
            print(f"  {error}")
        return 1

    yaml_count = sum(1 for _ in playbooks_dir.rglob("*.yaml"))
    print(f"OK: All {yaml_count} playbook(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())

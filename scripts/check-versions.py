#!/usr/bin/env python3
"""
Version consistency check - ensures all 4 version files are in sync.

Run before tagging a release, or add to CI via:
    python3 scripts/check-versions.py

Exits 0 if all versions match, 1 if they differ.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def get_package_json_version(path: Path) -> str:
    data = json.loads(path.read_text())
    return data["version"]


def get_pyproject_version(path: Path) -> str:
    text = path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find version in {path}")
    return match.group(1)


def get_python_init_version(path: Path) -> str:
    text = path.read_text()
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find __version__ in {path}")
    return match.group(1)


def main() -> int:
    sources = {
        "package.json": get_package_json_version(ROOT / "package.json"),
        "frontend/package.json": get_package_json_version(ROOT / "frontend" / "package.json"),
        "backend/pyproject.toml": get_pyproject_version(ROOT / "backend" / "pyproject.toml"),
        "backend/__init__.py": get_python_init_version(
            ROOT / "backend" / "ignition_toolkit" / "__init__.py"
        ),
    }

    versions = set(sources.values())
    if len(versions) == 1:
        print(f"✓ All version files agree: {next(iter(versions))}")
        for name, ver in sources.items():
            print(f"  {name}: {ver}")
        return 0
    else:
        print("✗ Version mismatch detected!", file=sys.stderr)
        for name, ver in sources.items():
            print(f"  {name}: {ver}", file=sys.stderr)
        print(
            "\nFix: update all 4 files to the same version before tagging.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

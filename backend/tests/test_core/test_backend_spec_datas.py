"""
Guard test: every non-Python file bundled under ``ignition_toolkit/`` must be
covered by a ``backend.spec`` ``datas`` entry, or explicitly allowlisted here.

Prevents a repeat of the 2026-07 UDT Builder bug: ``udt/templates/*.json``
existed in the source tree but was never added to ``backend.spec``, so the
PyInstaller-frozen build silently shipped without it (blank UDT Builder page
in v3.3.0, ``GET /api/udt/templates`` returning ``[]``). The same class of bug
was found in four more places (api/data, exchange/selectors.json,
browser/component_discovery.js) — all fixed alongside this
test.
"""

import re
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent.parent
SPEC_PATH = BACKEND_DIR / "backend.spec"
PACKAGE_DIR = BACKEND_DIR / "ignition_toolkit"

# Files intentionally NOT bundled into the frozen app. Keep this list
# minimal, and comment *why* for each entry. Paths are relative to
# ignition_toolkit/.
ALLOWLIST = {
    # Developer-facing documentation, not read at runtime.
    "stackbuilder/README.md",
}


def _spec_data_source_paths() -> list[Path]:
    """Extract every literal ``backend_dir / '...' / '...'`` join from backend.spec's datas list."""
    text = SPEC_PATH.read_text(encoding="utf-8")
    paths = []
    for match in re.finditer(r"backend_dir((?:\s*/\s*'[^']*')+)", text):
        segments = re.findall(r"'([^']*)'", match.group(1))
        paths.append(BACKEND_DIR.joinpath(*segments))
    return paths


def test_spec_data_source_paths_exist():
    """Every source path referenced in backend.spec's datas must exist (catches typos/renames)."""
    spec_paths = _spec_data_source_paths()
    assert spec_paths, "Failed to extract any datas source paths from backend.spec - regex broken?"

    for path in spec_paths:
        assert path.exists(), (
            f"backend.spec datas references '{path}', which does not exist on disk. "
            "Fix the path in backend.spec (typo or rename?)."
        )


def test_all_package_data_files_are_bundled():
    """
    Every non-.py file under ignition_toolkit/ must live under one of
    backend.spec's bundled datas source paths, or be explicitly allowlisted.
    """
    spec_paths = _spec_data_source_paths()

    missing = []
    for path in PACKAGE_DIR.rglob("*"):
        if path.is_dir():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix in (".py", ".pyc"):
            continue

        rel = path.relative_to(PACKAGE_DIR)
        if rel.as_posix() in ALLOWLIST:
            continue

        covered = any(path == spec_path or spec_path in path.parents for spec_path in spec_paths)
        if not covered:
            missing.append(rel.as_posix())

    assert not missing, (
        "The following ignition_toolkit/ data files are not bundled by backend.spec's "
        "datas list, so they will be missing from the frozen (PyInstaller) build:\n"
        + "\n".join(f"  - {m}" for m in missing)
        + "\n\nFix: add the file/directory to `datas` in backend.spec, AND make sure the "
        "consumer resolves the bundled path in frozen mode (see "
        "ignition_toolkit/stackbuilder/catalog.py:_get_data_path for the pattern) - or, if "
        "the file is intentionally not needed at runtime, add it to ALLOWLIST in this test "
        "with a comment explaining why."
    )

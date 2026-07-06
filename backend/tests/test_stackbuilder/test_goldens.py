"""
Golden-file snapshot tests (T4) for Stack Builder.

Snapshots every artefact `ComposeGenerator.generate()` produces for a curated
set of realistic stacks (docker_compose, env, readme, config_files,
startup_scripts) under `goldens/<stack_id>/` and diffs byte-exactly. Catches
accidental regressions in templates, README text, and startup scripts that
the pure sweeps (T1/T2 in test_singles_sweep.py / test_pairs_sweep.py)
wouldn't notice - those check structure, not content.
See docs/plans/stackbuilder-test-strategy.md (T4).

Run with `--update-goldens` to regenerate the snapshots after an intentional
generator change - see goldens/README.md for the full workflow and for the
list of normalisations applied to keep snapshots deterministic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.test_stackbuilder.golden_stacks import (
    GOLDEN_STACKS,
    GoldenStack,
    generate_stack,
    normalize_artifacts,
)

GOLDENS_DIR = Path(__file__).parent / "goldens"


def _artifact_files(result: dict[str, Any]) -> dict[str, str]:
    """Flatten a generate() result into {relative_path: content} for snapshotting."""
    files = {
        "docker-compose.yml": result["docker_compose"],
        # Stored as env.snapshot, not ".env": dotfile-named env files are
        # blocked by the workspace secrets-guard hook and excluded by the
        # repo .gitignore, so a literal .env golden silently never reaches
        # CI (which is exactly what happened on the first Windows run).
        "env.snapshot": result["env"],
        "README.md": result["readme"],
    }
    for rel_path, content in result.get("config_files", {}).items():
        files[f"config_files/{rel_path}"] = content
    for name, content in result.get("startup_scripts", {}).items():
        files[f"startup_scripts/{name}"] = content
    return files


def _write_golden(stack_dir: Path, files: dict[str, str]) -> None:
    """Replace stack_dir's contents with `files` (removing stale artefacts first)."""
    if stack_dir.exists():
        for existing in sorted(stack_dir.rglob("*"), reverse=True):
            if existing.is_file():
                existing.unlink()
    for rel_path, content in files.items():
        path = stack_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if stack_dir.exists():
        for existing in sorted(stack_dir.rglob("*"), reverse=True):
            if existing.is_dir() and not any(existing.iterdir()):
                existing.rmdir()


def _read_golden(stack_dir: Path) -> dict[str, str]:
    if not stack_dir.exists():
        return {}
    return {
        # as_posix(): golden keys must use "/" on every platform - plain
        # str() yields backslashes on Windows, breaking every comparison.
        p.relative_to(stack_dir).as_posix(): p.read_text(encoding="utf-8")
        for p in stack_dir.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("stack", GOLDEN_STACKS, ids=[s.id for s in GOLDEN_STACKS])
def test_golden_stack_matches_snapshot(stack: GoldenStack, update_goldens: bool) -> None:
    """Every curated stack's generated artefacts match (or, with --update-goldens, become) its snapshot."""
    result = normalize_artifacts(generate_stack(stack))
    actual_files = _artifact_files(result)
    stack_dir = GOLDENS_DIR / stack.id

    if update_goldens:
        _write_golden(stack_dir, actual_files)

    expected_files = _read_golden(stack_dir)
    assert expected_files, (
        f"{stack.id}: no golden snapshot found at {stack_dir} - "
        "run with --update-goldens to create it"
    )

    assert set(actual_files) == set(expected_files), (
        f"{stack.id}: generated artefact set differs from golden "
        f"(missing={sorted(set(expected_files) - set(actual_files))}, "
        f"extra={sorted(set(actual_files) - set(expected_files))})"
    )
    for rel_path, content in actual_files.items():
        assert (
            content == expected_files[rel_path]
        ), f"{stack.id}: {rel_path} differs from its golden snapshot"


def test_golden_stack_ids_are_unique() -> None:
    """Guard against a copy-paste id collision silently shadowing a stack."""
    ids = [s.id for s in GOLDEN_STACKS]
    assert len(ids) == len(set(ids)), "duplicate golden stack ids"


def test_golden_stack_count_within_plan_range() -> None:
    """docs/plans/stackbuilder-test-strategy.md (T4) calls for 6-8 curated stacks."""
    assert 6 <= len(GOLDEN_STACKS) <= 8

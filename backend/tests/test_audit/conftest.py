"""Shared fixtures for the audit test suite."""

from pathlib import Path

import pytest

from ignition_toolkit.audit.project import PerspectiveProject

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


def load_project(relative_path: str) -> PerspectiveProject:
    """Load a PerspectiveProject from a named directory under fixtures/."""
    return PerspectiveProject.load(FIXTURES_DIR / relative_path)

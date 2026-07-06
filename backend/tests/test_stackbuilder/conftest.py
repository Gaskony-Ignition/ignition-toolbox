"""Pytest configuration local to the Stack Builder test package: golden-file update flag."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help=(
            "Regenerate backend/tests/test_stackbuilder/goldens/ snapshots from the "
            "current generator output instead of comparing against them. See "
            "goldens/README.md."
        ),
    )


@pytest.fixture
def update_goldens(request: pytest.FixtureRequest) -> bool:
    """True when the suite was run with --update-goldens."""
    return bool(request.config.getoption("--update-goldens"))

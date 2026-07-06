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


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    Force-skip `slow`-marked tests (T5 live-smoke, test_live_smoke.py) unless the
    caller explicitly selected via `-m`.

    There's no repo-wide `addopts` deselecting `slow`/`integration` by default (see
    pyproject.toml), so a bare `pytest tests/test_stackbuilder -q` would otherwise try
    to actually `docker compose up` real stacks - slow, network-dependent, and
    explicitly documented as "manual/on-demand, NOT CI" in
    docs/plans/stackbuilder-test-strategy.md (T5). Respect any explicit `-m`
    selection (e.g. `-m slow` or `-m "integration and slow"`) so the tests remain
    runnable on demand.
    """
    if config.option.markexpr:
        return
    skip_slow = pytest.mark.skip(reason="slow live-smoke test - run explicitly with -m slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)

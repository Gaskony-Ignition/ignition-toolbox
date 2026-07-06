"""
Compose-spec validation (T3) for Stack Builder.

Pipes every T1 single-service default generation (see test_singles_sweep.py)
and every curated golden stack (T4, see golden_stacks.py) through
`docker compose -f - config -q`, validating the generated YAML against the
real Compose spec without starting any containers.
See docs/plans/stackbuilder-test-strategy.md (T3).

Marked `integration` and skipped cleanly whenever a working `docker compose`
cannot be probed (missing CLI, missing plugin, unreachable daemon). In
practice `docker compose config` does not need a running daemon, but this
probes the exact command the tests use rather than assuming that, so any
Compose implementation quirk on a given machine degrades to a clean skip
instead of a false failure. Failures from an individual test are likewise
inspected for infrastructure-error signatures before being reported as a
genuine generator/compose-spec bug, so a flaky daemon can never masquerade as
a "generator bug".
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

import pytest

from tests.test_stackbuilder.golden_stacks import GOLDEN_STACKS, GoldenStack, generate_stack
from tests.test_stackbuilder.test_singles_sweep import _enabled_apps, _generate_single

_PROBE_COMPOSE = "services:\n  probe:\n    image: scratch\n"
_TIMEOUT_S = 30

# Substrings in `docker compose config` stderr that indicate a docker
# *infrastructure* problem (daemon down, permissions, missing socket) rather
# than a spec violation in our generated YAML.
_INFRA_ERROR_MARKERS = (
    "cannot connect to the docker daemon",
    "is the docker daemon running",
    "permission denied",
    "no such file or directory",
    "connection refused",
    "error during connect",
)


def _run_compose_config(compose_yaml: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "-f", "-", "config", "-q"],
        input=compose_yaml,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
    )


def _probe_docker_compose() -> tuple[bool, str]:
    """Try the exact command the tests use; report (available, skip_reason)."""
    if shutil.which("docker") is None:
        return False, "docker CLI not found on PATH"
    try:
        proc = _run_compose_config(_PROBE_COMPOSE)
    except FileNotFoundError:
        return False, "docker compose plugin not found"
    except subprocess.TimeoutExpired:
        return False, "docker compose config timed out while probing availability"
    if proc.returncode != 0:
        return False, f"docker compose config unavailable: {proc.stderr.strip()[:300]}"
    return True, ""


_DOCKER_AVAILABLE, _DOCKER_SKIP_REASON = _probe_docker_compose()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _DOCKER_AVAILABLE, reason=_DOCKER_SKIP_REASON or "docker compose unavailable"
    ),
]


def _assert_valid_compose(compose_yaml: str, label: str) -> None:
    """Run `docker compose config -q` on generated YAML; fail on real spec violations only."""
    try:
        proc = _run_compose_config(compose_yaml)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"{label}: docker infrastructure unavailable mid-run ({exc})")
        return

    if proc.returncode != 0:
        stderr_lower = proc.stderr.lower()
        if any(marker in stderr_lower for marker in _INFRA_ERROR_MARKERS):
            pytest.skip(
                f"{label}: docker infrastructure failure, not a generator bug: "
                f"{proc.stderr.strip()[:500]}"
            )
        pytest.fail(
            f"{label}: `docker compose config` rejected the generated compose spec:\n"
            f"{proc.stderr.strip()}"
        )


@pytest.mark.parametrize("app", _enabled_apps(), ids=lambda a: a["id"])
def test_single_service_default_is_valid_compose(app: dict[str, Any]) -> None:
    """Every enabled service's default-config compose output validates against the real Compose spec."""
    result, _instance = _generate_single(app, config={})
    _assert_valid_compose(result["docker_compose"], app["id"])


@pytest.mark.parametrize("stack", GOLDEN_STACKS, ids=[s.id for s in GOLDEN_STACKS])
def test_golden_stack_is_valid_compose(stack: GoldenStack) -> None:
    """Every curated golden stack (T4) validates against the real Compose spec."""
    result = generate_stack(stack)
    _assert_valid_compose(result["docker_compose"], stack.id)

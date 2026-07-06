"""
Live smoke tests (T5) for Stack Builder.

Actually `docker compose up -d` two curated, small stacks, poll their real health
endpoints, and tear down with volumes. This is the only tier in the test strategy
(docs/plans/stackbuilder-test-strategy.md) that touches Docker for real - "manual /
on-demand, NOT CI". Run explicitly:

    cd backend && .venv/bin/python -m pytest tests/test_stackbuilder/test_live_smoke.py \\
        -m "integration and slow" -q

Marked `integration` and `slow`; `tests/test_stackbuilder/conftest.py` force-skips
`slow` tests unless the caller passes an explicit `-m` selection, so a bare
`pytest tests/test_stackbuilder -q` never triggers this file.

Safety model (this host also runs an unrelated, host-networked Ignition gateway
container - `ignition-module-testing` - that must never be touched):
  - Every host port used by the generated stacks is remapped into 18000-18999 via
    each service's `configurable_options` (see catalog.json / compose_generator.py
    `_get_host_port`), and a bind-check skips cleanly if any chosen port is busy.
  - Every stack runs under a fresh, random `docker compose -p toolbox-smoke-<hex8>`
    project name. Note: `ComposeGenerator` sets each service's `container_name`
    explicitly to `f"{global_settings.stack_name}-{instance_name}"` rather than
    letting Compose derive it from the project - so the project name alone would
    NOT guarantee unique container names. This is why the two stacks below call
    `ComposeGenerator().generate(..., global_settings=GlobalSettings(stack_name=project))`
    directly (the same class `golden_stacks.generate_stack()` wraps) instead of the
    golden-stack helper, which hardcodes `stack_name="iiot-stack"`: passing the
    random project name as `stack_name` too makes container names unique as well,
    so a leftover/interrupted prior run can never collide with a new one.
  - Teardown (`docker compose down -v --remove-orphans`) runs in a `finally`, which
    Python guarantees executes on any exception unwinding through it, including
    KeyboardInterrupt.
  - Before and after each stack, `docker ps -a` container names are snapshotted and
    compared: no leftover container for our project may remain, and the pre-existing
    container set (e.g. `ignition-module-testing`) must be byte-for-byte unchanged.
  - Images are pulled (with a bounded, per-repository timeout) before `up -d` runs,
    so a slow/broken registry surfaces as a clean `pytest.skip`, never a false
    "generator bug" failure. Ignition's tag is chosen from whatever is already
    present locally (`docker images`) when possible, to avoid an ~1-2GB pull.
"""

from __future__ import annotations

import contextlib
import secrets
import socket
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

from ignition_toolkit.stackbuilder.compose_generator import ComposeGenerator, GlobalSettings
from tests.test_stackbuilder.golden_stacks import _instance

pytestmark = [pytest.mark.integration, pytest.mark.slow]

# --- Port allocation (CRITICAL: must never collide with the host's real
# ignition-module-testing container or anything else) --------------------------

MONITORING_PORTS = {"prometheus": 18090, "grafana": 18091, "dozzle": 18092}
IGNITION_POSTGRES_PORTS = {"ignition_http": 18088, "ignition_https": 18443, "postgres": 18432}

POSTGRES_USER = "postgres"

_HTTP_TIMEOUT_S = 5.0
_UP_TIMEOUT_S = 180
_DOWN_TIMEOUT_S = 180
_IMAGE_PULL_TIMEOUT_S = {
    # Ignition images are ~1-2GB; everything else here is small.
    "inductiveautomation/ignition": 600,
}
_DEFAULT_IMAGE_PULL_TIMEOUT_S = 180

# stderr substrings that indicate a Docker *infrastructure* problem (daemon down,
# registry unreachable, disk full) rather than a real generator/compose-spec bug.
_INFRA_ERROR_MARKERS = (
    "cannot connect to the docker daemon",
    "is the docker daemon running",
    "permission denied",
    "no such file or directory",
    "connection refused",
    "error during connect",
    "timeout",
    "no space left on device",
)


# --- Docker/daemon availability probe (module-level, like test_compose_spec.py) --


def _probe_docker() -> tuple[bool, str]:
    try:
        proc = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=15)
    except FileNotFoundError:
        return False, "docker CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "docker info timed out while probing daemon availability"
    if proc.returncode != 0:
        return False, f"docker daemon unreachable: {proc.stderr.strip()[:300]}"
    return True, ""


_DOCKER_AVAILABLE, _DOCKER_SKIP_REASON = _probe_docker()


# --- Small helpers --------------------------------------------------------------


def _assert_ports_free(ports: Iterable[int]) -> None:
    """Skip cleanly (never fail) if any smoke-test port is already bound on this host."""
    busy = []
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                busy.append(port)
    if busy:
        pytest.skip(
            f"host port(s) {busy} in the 18000-18999 smoke-test range are already "
            "in use - skipping rather than risk clobbering something else"
        )


def _docker_container_names() -> set[str]:
    proc = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        return set()
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def _assert_docker_state_unchanged(before: set[str], project: str) -> None:
    after = _docker_container_names()
    leaked = {name for name in after if project in name}
    assert not leaked, f"teardown left containers behind for project '{project}': {sorted(leaked)}"
    assert after == before, (
        "the host's pre-existing container set changed across the smoke test run "
        f"(missing afterwards={sorted(before - after)}, "
        f"unexpected new leftovers={sorted(after - before)})"
    )


def _local_image_tags(repository: str) -> set[str]:
    proc = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        return set()
    return {
        line.strip()
        for line in proc.stdout.splitlines()
        if line.strip().startswith(f"{repository}:") and ":<none>" not in line
    }


def _pick_available_or_default(repository: str, default_tag: str) -> str:
    """
    Prefer a tag already pulled locally for `repository`, to avoid an unnecessary
    (possibly large, e.g. ~1-2GB for Ignition) network pull; fall back to
    `default_tag` when nothing is present (the caller's image-pull step then
    fetches it with a bounded timeout).
    """
    local = _local_image_tags(repository)
    if f"{repository}:{default_tag}" in local:
        return default_tag
    if local:
        return sorted(local)[0].split(":", 1)[1]
    return default_tag


def _extract_images(compose_yaml: str) -> list[str]:
    doc = yaml.safe_load(compose_yaml)
    return [svc["image"] for svc in doc.get("services", {}).values() if "image" in svc]


def _ensure_image(image: str) -> tuple[bool, str]:
    """Pull `image` if missing locally. Returns (ok, detail); never raises."""
    inspect = subprocess.run(
        ["docker", "image", "inspect", image], capture_output=True, text=True, timeout=15
    )
    if inspect.returncode == 0:
        return True, "already present locally"

    repo = image.split(":", 1)[0]
    timeout_s = _IMAGE_PULL_TIMEOUT_S.get(repo, _DEFAULT_IMAGE_PULL_TIMEOUT_S)
    try:
        pull = subprocess.run(
            ["docker", "pull", image], capture_output=True, text=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired:
        return False, f"pull timed out after {timeout_s}s"
    if pull.returncode != 0:
        return False, f"pull failed: {pull.stderr.strip()[:400]}"
    return True, f"pulled ({timeout_s}s budget)"


def _ensure_images(images: list[str]) -> None:
    """
    Make sure every image `up -d` will need is available, pulling with a bounded
    timeout first. A pull failure/timeout is infrastructure (network, registry),
    never a generator bug, so it is a clean skip rather than a test failure.
    """
    for image in images:
        ok, detail = _ensure_image(image)
        print(f"[image] {image}: {detail}")
        if not ok:
            pytest.skip(f"could not make image '{image}' available: {detail}")


def _write_artifacts(stack_dir: Path, generated: dict[str, Any]) -> None:
    """Write generate()'s output to disk exactly as StackBuilder would export it."""
    (stack_dir / "docker-compose.yml").write_text(generated["docker_compose"], encoding="utf-8")
    (stack_dir / ".env").write_text(generated.get("env", ""), encoding="utf-8")
    for rel_path, content in generated.get("config_files", {}).items():
        full_path = stack_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
    for rel_path, content in generated.get("startup_scripts", {}).items():
        full_path = stack_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")


@contextlib.contextmanager
def _running_stack(stack_dir: Path, project: str) -> Iterator[None]:
    """
    `docker compose up -d` on enter; `docker compose down -v --remove-orphans` on
    exit NO MATTER WHAT (normal return, assertion failure, or KeyboardInterrupt -
    a `finally` block runs for all of these as the exception unwinds through it).
    """
    up = subprocess.run(
        ["docker", "compose", "-p", project, "up", "-d"],
        cwd=stack_dir,
        capture_output=True,
        text=True,
        timeout=_UP_TIMEOUT_S,
    )
    if up.returncode != 0:
        # Nothing (or only partial state) came up; still attempt a cleanup pass in
        # case some containers/networks/volumes were created before the failure.
        subprocess.run(
            ["docker", "compose", "-p", project, "down", "-v", "--remove-orphans"],
            cwd=stack_dir,
            capture_output=True,
            text=True,
            timeout=_DOWN_TIMEOUT_S,
        )
        stderr_lower = up.stderr.lower()
        if any(marker in stderr_lower for marker in _INFRA_ERROR_MARKERS):
            pytest.skip(f"docker compose up infrastructure failure: {up.stderr.strip()[:500]}")
        pytest.fail(f"`docker compose up -d` failed for project '{project}':\n{up.stderr.strip()}")

    try:
        yield
    finally:
        down = subprocess.run(
            ["docker", "compose", "-p", project, "down", "-v", "--remove-orphans"],
            cwd=stack_dir,
            capture_output=True,
            text=True,
            timeout=_DOWN_TIMEOUT_S,
        )
        if down.returncode != 0:
            # Teardown is non-negotiable - make noise, but don't swallow whatever
            # exception (if any) is already propagating out of the `try`.
            print(
                f"WARNING: `docker compose down` for project '{project}' exited "
                f"{down.returncode}: {down.stderr.strip()[:500]}"
            )


def _poll_until(
    check: Callable[[], tuple[bool, str]], timeout_s: float, interval_s: float, label: str
) -> float:
    """Poll `check` until it reports healthy or `timeout_s` elapses. Returns elapsed seconds."""
    start = time.monotonic()
    deadline = start + timeout_s
    last_detail = "never attempted"
    while time.monotonic() < deadline:
        ok, last_detail = check()
        if ok:
            return time.monotonic() - start
        time.sleep(interval_s)
    pytest.fail(
        f"{label}: did not become healthy within {timeout_s:.0f}s "
        f"(this is a real health-check failure, not an infra skip; last status: {last_detail})"
    )


# --- Health checks ---------------------------------------------------------------


def _check_http_ok(url: str) -> tuple[bool, str]:
    try:
        resp = httpx.get(url, timeout=_HTTP_TIMEOUT_S)
    except httpx.HTTPError as exc:
        return False, f"request failed: {exc}"
    return resp.status_code == 200, f"HTTP {resp.status_code}"


def _check_grafana_health(port: int) -> tuple[bool, str]:
    try:
        resp = httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=_HTTP_TIMEOUT_S)
    except httpx.HTTPError as exc:
        return False, f"request failed: {exc}"
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    try:
        data = resp.json()
    except ValueError:
        return False, f"non-JSON body: {resp.text[:200]!r}"
    return data.get("database") == "ok", f"body={data}"


def _check_pg_isready(container: str, user: str) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["docker", "exec", container, "pg_isready", "-U", user],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False, "pg_isready exec timed out"
    except FileNotFoundError:
        return False, "docker CLI unavailable"
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def _check_ignition_running(port: int) -> tuple[bool, str]:
    try:
        resp = httpx.get(f"http://127.0.0.1:{port}/StatusPing", timeout=_HTTP_TIMEOUT_S)
    except httpx.HTTPError as exc:
        return False, f"request failed: {exc}"
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    try:
        data = resp.json()
    except ValueError:
        return False, f"non-JSON body: {resp.text[:200]!r}"
    state = data.get("state")
    return state == "RUNNING", f"state={state!r}"


def _check_grafana_prometheus_datasource(port: int) -> tuple[bool, str]:
    """
    Proves the compose_generator.py fix in this change actually works: Grafana's
    auto-provisioned datasource config (configs/<grafana>/provisioning/datasources/
    auto.yaml) is now bind-mounted, so the Prometheus datasource should really load.
    """
    try:
        resp = httpx.get(
            f"http://127.0.0.1:{port}/api/datasources",
            auth=("admin", "admin"),
            timeout=_HTTP_TIMEOUT_S,
        )
    except httpx.HTTPError as exc:
        return False, f"request failed: {exc}"
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    datasources = resp.json()
    return (
        any(ds.get("type") == "prometheus" for ds in datasources),
        f"datasources={datasources}",
    )


# --- Tests -------------------------------------------------------------------


def test_monitoring_stack_smoke() -> None:
    """Prometheus + Grafana + Dozzle: small images, fast to start, no license/EULA."""
    if not _DOCKER_AVAILABLE:
        pytest.skip(_DOCKER_SKIP_REASON)
    _assert_ports_free(MONITORING_PORTS.values())

    project = f"toolbox-smoke-{secrets.token_hex(4)}"
    instances = [
        _instance("prometheus", "prometheus", {"port": MONITORING_PORTS["prometheus"]}),
        _instance("grafana", "grafana", {"port": MONITORING_PORTS["grafana"]}),
        _instance("dozzle", "dozzle", {"port": MONITORING_PORTS["dozzle"]}),
    ]
    generated = ComposeGenerator().generate(
        instances, global_settings=GlobalSettings(stack_name=project)
    )

    before = _docker_container_names()
    run_start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="toolbox-smoke-monitoring-") as tmp:
        stack_dir = Path(tmp)
        _write_artifacts(stack_dir, generated)
        _ensure_images(_extract_images(generated["docker_compose"]))

        with _running_stack(stack_dir, project):
            up_elapsed = time.monotonic() - run_start

            prom_elapsed = _poll_until(
                lambda: _check_http_ok(
                    f"http://127.0.0.1:{MONITORING_PORTS['prometheus']}/-/ready"
                ),
                timeout_s=60,
                interval_s=2,
                label="prometheus /-/ready",
            )
            grafana_elapsed = _poll_until(
                lambda: _check_grafana_health(MONITORING_PORTS["grafana"]),
                timeout_s=60,
                interval_s=2,
                label="grafana /api/health",
            )
            dozzle_elapsed = _poll_until(
                lambda: _check_http_ok(f"http://127.0.0.1:{MONITORING_PORTS['dozzle']}/"),
                timeout_s=60,
                interval_s=2,
                label="dozzle root page",
            )
            ds_elapsed = _poll_until(
                lambda: _check_grafana_prometheus_datasource(MONITORING_PORTS["grafana"]),
                timeout_s=30,
                interval_s=2,
                label="grafana auto-provisioned prometheus datasource",
            )

            print(
                f"[monitoring smoke] up: {up_elapsed:.1f}s, "
                f"prometheus ready: {prom_elapsed:.1f}s, "
                f"grafana healthy: {grafana_elapsed:.1f}s, dozzle: {dozzle_elapsed:.1f}s, "
                f"datasource provisioned: {ds_elapsed:.1f}s"
            )

    _assert_docker_state_unchanged(before, project)


def test_ignition_postgres_stack_smoke() -> None:
    """Ignition + Postgres: the canonical StackBuilder pairing, with a real gateway boot."""
    if not _DOCKER_AVAILABLE:
        pytest.skip(_DOCKER_SKIP_REASON)
    _assert_ports_free(IGNITION_POSTGRES_PORTS.values())

    ignition_version = _pick_available_or_default("inductiveautomation/ignition", "latest")
    postgres_version = _pick_available_or_default("postgres", "latest")
    print(
        f"[ignition+postgres smoke] using ignition:{ignition_version}, "
        f"postgres:{postgres_version}"
    )

    project = f"toolbox-smoke-{secrets.token_hex(4)}"
    instances = [
        _instance(
            "ignition",
            "ignition",
            {
                "http_port": IGNITION_POSTGRES_PORTS["ignition_http"],
                "https_port": IGNITION_POSTGRES_PORTS["ignition_https"],
                "version": ignition_version,
            },
        ),
        _instance(
            "postgres",
            "postgres",
            {"port": IGNITION_POSTGRES_PORTS["postgres"], "version": postgres_version},
        ),
    ]
    generated = ComposeGenerator().generate(
        instances, global_settings=GlobalSettings(stack_name=project)
    )

    before = _docker_container_names()
    run_start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="toolbox-smoke-ignition-") as tmp:
        stack_dir = Path(tmp)
        _write_artifacts(stack_dir, generated)
        _ensure_images(_extract_images(generated["docker_compose"]))

        with _running_stack(stack_dir, project):
            up_elapsed = time.monotonic() - run_start
            postgres_container = f"{project}-postgres"

            pg_elapsed = _poll_until(
                lambda: _check_pg_isready(postgres_container, POSTGRES_USER),
                timeout_s=60,
                interval_s=2,
                label="postgres pg_isready",
            )
            # Real gateway boot (EULA acceptance, internal DB init, module load) can
            # take minutes on a cold volume - allow up to 4 minutes as instructed.
            ignition_elapsed = _poll_until(
                lambda: _check_ignition_running(IGNITION_POSTGRES_PORTS["ignition_http"]),
                timeout_s=240,
                interval_s=5,
                label="ignition /StatusPing state=RUNNING",
            )

            print(
                f"[ignition+postgres smoke] up: {up_elapsed:.1f}s, "
                f"postgres ready: {pg_elapsed:.1f}s, ignition RUNNING: {ignition_elapsed:.1f}s"
            )

    _assert_docker_state_unchanged(before, project)

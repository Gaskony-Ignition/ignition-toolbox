"""
Runtime audit results — bridges Mode B (playbook) execution to the audit report.

``report.py`` renders Mode A (static analysis of a project export). This
module turns the *runtime* side — a completed execution of one of the
`perspective/*.yaml` library playbooks (``session_smoke``, ``page_crawl``,
``navigation_audit``, ``visual_baseline``) against a live gateway — into the
same small typed shape, so :class:`~ignition_toolkit.audit.report.AuditReport`
can optionally include a "Runtime checks" section alongside the static
findings.

Nothing here talks to a gateway or the playbook engine directly; it only
consumes an already-finished
:class:`ignition_toolkit.playbook.models.ExecutionState` (what
``PlaybookEngine.execute_playbook`` returns) and derives page-level outcomes
from its step results. This keeps the audit package's only coupling to the
playbook engine confined to one function.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ignition_toolkit.playbook.models import ExecutionState, StepStatus

logger = logging.getLogger(__name__)

# Matches the Perspective client URL path after the project name, e.g.
# ".../data/perspective/client/ToolboxAudit/page2" -> "/page2", and
# ".../data/perspective/client/ToolboxAudit/" (or no trailing segment at
# all) -> "/".
_CLIENT_URL_PATH_RE = re.compile(r"/data/perspective/client/[^/]+(/.*)?$")


def _extract_page_path(url: str) -> str:
    """Best-effort extraction of the page-config route from a client URL.

    Falls back to returning the raw URL unchanged if it doesn't look like a
    Perspective client URL at all (e.g. a non-Perspective playbook step),
    so callers always get a usable string.
    """
    match = _CLIENT_URL_PATH_RE.search(url)
    if not match:
        return url
    path = match.group(1)
    return path if path else "/"


@dataclass(frozen=True)
class PageRuntimeResult:
    """Runtime outcome for a single visit to a page-config route.

    One instance is produced per ``browser.navigate`` call observed in the
    execution's step results (see :func:`build_runtime_results_from_execution`)
    — a playbook that visits the same route more than once (e.g.
    ``navigation_audit.yaml``, which returns Home to reach the navigation
    button) yields one entry per visit, not a deduplicated one, so the
    report reflects exactly what happened at runtime.
    """

    path: str
    loaded_ok: bool
    load_time_ms: float | None = None
    console_errors: list[str] = field(default_factory=list)
    screenshot_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "loaded_ok": self.loaded_ok,
            "load_time_ms": self.load_time_ms,
            "console_errors": list(self.console_errors),
            "screenshot_path": self.screenshot_path,
            "error": self.error,
        }


@dataclass(frozen=True)
class RuntimeAuditResults:
    """Runtime checks section: one playbook execution's page-by-page outcomes."""

    playbook_name: str
    executed_at: datetime
    pages: list[PageRuntimeResult]

    @property
    def all_pages_loaded_ok(self) -> bool:
        """True if every page visit in this execution loaded without failure.

        Vacuously true for an empty page list (nothing failed because
        nothing was checked) — callers that care about "were there actually
        any checks" should also look at ``len(pages)``.
        """
        return all(page.loaded_ok for page in self.pages)

    def to_dict(self) -> dict[str, Any]:
        return {
            "playbook_name": self.playbook_name,
            "executed_at": self.executed_at.isoformat(),
            "pages": [page.to_dict() for page in self.pages],
            "all_pages_loaded_ok": self.all_pages_loaded_ok,
        }


def build_runtime_results_from_execution(execution: ExecutionState) -> RuntimeAuditResults:
    """Derive :class:`RuntimeAuditResults` from a finished playbook execution.

    Groups the execution's step results into "page runs": every
    ``browser.navigate`` step (identified by its output shape —
    ``{"status": "navigated", "url": ...}``, as produced by
    ``BrowserNavigateHandler``) starts a new run, which absorbs the
    following steps until the next navigate (or the end of the playbook):

    - a ``browser.wait`` step whose output is ``{"status": "found", ...}``
      supplies ``load_time_ms`` (elapsed time from the navigate step's
      start to the wait step's completion) and confirms the page rendered;
    - a ``browser.screenshot`` step's output supplies ``screenshot_path``;
    - any step with :class:`StepStatus.FAILED` marks the page run as
      ``loaded_ok=False`` and carries its error message through.

    This makes no assumption about step IDs or which perspective playbook
    produced the execution — it works for ``page_crawl.yaml``,
    ``navigation_audit.yaml``, and ``visual_baseline.yaml`` alike, since all
    three share the same navigate/wait/screenshot step shapes (see
    ``backend/playbooks/perspective/``).

    Known limitation: no playbook step type currently captures browser
    console errors, so ``console_errors`` is always ``[]`` today. The field
    is kept on :class:`PageRuntimeResult` so a future console-capturing step
    type (or a ``perspective.discover_page`` enhancement) can populate it
    without another report-layer change.

    Steps before the first navigate (e.g. a planning ``utility.log`` step)
    are ignored — they aren't scoped to any page.

    A ``perspective.verify_navigation`` step whose output reports a *different*
    path than the currently-tracked one (see ``navigation_audit.yaml``, which
    verifies the in-app navigation button drove the client from "/" to
    "/page2" with no intervening ``browser.navigate`` call — the URL only
    changes because of Perspective's own client-side routing) is treated as
    a second kind of page-run boundary for exactly this reason: without it,
    the button-driven visit would be silently folded into the run started
    by the preceding ``browser.navigate`` call, and a screenshot taken after
    the button click would be mis-attributed to the page that click
    navigated *away* from. A same-path ``verify_navigation`` (the common
    case: confirming a plain ``browser.navigate`` landed where expected) is
    not a boundary — it only supplies ``load_time_ms`` if no ``browser.wait``
    already did.

    Known limitation: if the ``browser.navigate`` step itself fails (e.g.
    the gateway is unreachable), :class:`~ignition_toolkit.playbook.step_executor.StepExecutor`
    records no ``output`` for that step (only ``error``), so there is no
    URL to recover the page path from — that visit is skipped from
    ``pages`` entirely rather than reported with an empty path. The
    execution's own ``status``/``error`` still reflect the failure; callers
    that need "did the whole execution succeed" should check those, not
    just ``RuntimeAuditResults.all_pages_loaded_ok``.
    """
    pages: list[PageRuntimeResult] = []

    current_path: str | None = None
    current_started_at: datetime | None = None
    current_rendered_at: datetime | None = None
    current_screenshot: str | None = None
    current_failed: bool = False
    current_error: str | None = None

    def flush() -> None:
        if current_path is None:
            return
        load_time_ms = None
        if current_started_at is not None and current_rendered_at is not None:
            load_time_ms = (current_rendered_at - current_started_at).total_seconds() * 1000
        pages.append(
            PageRuntimeResult(
                path=current_path,
                loaded_ok=not current_failed,
                load_time_ms=load_time_ms,
                console_errors=[],
                screenshot_path=current_screenshot,
                error=current_error,
            )
        )

    def start_run(path: str, started_at: datetime | None) -> None:
        nonlocal current_path, current_started_at, current_rendered_at
        nonlocal current_screenshot, current_failed, current_error
        current_path = path
        current_started_at = started_at
        current_rendered_at = None
        current_screenshot = None
        current_failed = False
        current_error = None

    def is_navigate_output(output: dict[str, Any]) -> bool:
        return output.get("status") == "navigated" and "url" in output

    def is_verify_navigation_output(output: dict[str, Any]) -> bool:
        # perspective.verify_navigation's success shape includes both "url"
        # and "title"; browser.verify_text/verify happen to share the same
        # "status": "verified" string but never carry "url"/"title", so
        # checking for those keys disambiguates the two step types without
        # needing the step's declared type here (StepResult doesn't carry it).
        return output.get("status") == "verified" and "url" in output and "title" in output

    for step in execution.step_results:
        output = step.output or {}

        if is_navigate_output(output):
            flush()
            start_run(_extract_page_path(output["url"]), step.started_at)
            if step.status == StepStatus.FAILED:
                current_failed = True
                current_error = step.error
            continue

        if is_verify_navigation_output(output) and step.status == StepStatus.COMPLETED:
            observed_path = _extract_page_path(output["url"])
            if current_path is None:
                start_run(observed_path, step.started_at)
            elif observed_path != current_path:
                flush()
                start_run(observed_path, step.started_at)
            if current_rendered_at is None:
                current_rendered_at = step.completed_at
            continue

        if current_path is None:
            # No navigate/verify_navigation seen yet — not scoped to a page.
            continue

        if step.status == StepStatus.FAILED:
            current_failed = True
            current_error = current_error or step.error
        elif step.status == StepStatus.COMPLETED:
            if output.get("status") == "found" and current_rendered_at is None:
                current_rendered_at = step.completed_at
            if "screenshot" in output:
                current_screenshot = output["screenshot"]

    flush()

    executed_at = execution.completed_at or execution.started_at

    return RuntimeAuditResults(
        playbook_name=execution.playbook_name,
        executed_at=executed_at,
        pages=pages,
    )

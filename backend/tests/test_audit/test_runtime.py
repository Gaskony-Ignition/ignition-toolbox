"""Tests for runtime.py — deriving RuntimeAuditResults from a playbook execution.

Synthetic ExecutionState/StepResult objects are built directly (no real
browser/playbook engine involved) so these tests stay fast and don't need a
live gateway — they only exercise the step-result grouping logic. A separate
manual run against the docker gateway (see the Perspective Project Audit
Phase 5 report) proves the real playbooks produce step results this module
can actually consume.
"""

from datetime import datetime, timedelta

from ignition_toolkit.audit.runtime import (
    PageRuntimeResult,
    RuntimeAuditResults,
    _extract_page_path,
    build_runtime_results_from_execution,
)
from ignition_toolkit.playbook.models import (
    ExecutionState,
    ExecutionStatus,
    StepResult,
    StepStatus,
)

T0 = datetime(2026, 7, 6, 12, 0, 0)


def _navigate(
    step_id: str, url: str, started_at: datetime, status: StepStatus = StepStatus.COMPLETED
) -> StepResult:
    return StepResult(
        step_id=step_id,
        step_name=f"Navigate to {url}",
        status=status,
        started_at=started_at,
        completed_at=started_at + timedelta(milliseconds=50),
        output={"url": url, "status": "navigated"} if status == StepStatus.COMPLETED else None,
        error=None if status == StepStatus.COMPLETED else "navigation failed",
    )


def _wait(
    step_id: str,
    completed_at: datetime,
    selector: str = "[data-component-type]",
    status: StepStatus = StepStatus.COMPLETED,
    error: str | None = None,
) -> StepResult:
    return StepResult(
        step_id=step_id,
        step_name="Wait for render",
        status=status,
        started_at=completed_at - timedelta(milliseconds=10),
        completed_at=completed_at,
        output=(
            {"selector": selector, "status": "found"} if status == StepStatus.COMPLETED else None
        ),
        error=error,
    )


def _screenshot(step_id: str, path: str, at: datetime) -> StepResult:
    return StepResult(
        step_id=step_id,
        step_name="Screenshot",
        status=StepStatus.COMPLETED,
        started_at=at,
        completed_at=at + timedelta(milliseconds=5),
        output={"screenshot": path, "status": "captured"},
    )


def _verify_navigation(step_id: str, url: str, title: str, at: datetime) -> StepResult:
    return StepResult(
        step_id=step_id,
        step_name="Verify navigation",
        status=StepStatus.COMPLETED,
        started_at=at - timedelta(milliseconds=20),
        completed_at=at,
        output={
            "status": "verified",
            "url": url,
            "title": title,
            "message": "Navigation verified successfully",
        },
    )


def _click(step_id: str, at: datetime) -> StepResult:
    return StepResult(
        step_id=step_id,
        step_name="Click button",
        status=StepStatus.COMPLETED,
        started_at=at,
        completed_at=at + timedelta(milliseconds=15),
        output={"selector": "[data-component-path='C.0:2']", "status": "clicked", "force": False},
    )


def _log(step_id: str, at: datetime) -> StepResult:
    return StepResult(
        step_id=step_id,
        step_name="Log plan",
        status=StepStatus.COMPLETED,
        started_at=at,
        completed_at=at + timedelta(milliseconds=1),
        output={"logged": "plan", "level": "info"},
    )


def _execution(
    step_results: list[StepResult], playbook_name: str = "perspective/page_crawl.yaml"
) -> ExecutionState:
    return ExecutionState(
        execution_id="exec-1",
        playbook_name=playbook_name,
        status=ExecutionStatus.COMPLETED,
        started_at=T0,
        completed_at=step_results[-1].completed_at if step_results else T0,
        total_steps=len(step_results),
        step_results=step_results,
    )


class TestExtractPagePath:
    def test_extracts_trailing_path(self) -> None:
        assert (
            _extract_page_path("http://localhost:8088/data/perspective/client/ToolboxAudit/page2")
            == "/page2"
        )

    def test_root_path_with_trailing_slash(self) -> None:
        assert (
            _extract_page_path("http://localhost:8088/data/perspective/client/ToolboxAudit/") == "/"
        )

    def test_root_path_with_no_trailing_slash(self) -> None:
        assert (
            _extract_page_path("http://localhost:8088/data/perspective/client/ToolboxAudit") == "/"
        )

    def test_non_client_url_returned_unchanged(self) -> None:
        url = "http://localhost:8088/app/platform/system/licensing"
        assert _extract_page_path(url) == url


class TestBuildRuntimeResultsFromExecution:
    def test_two_successful_page_visits(self) -> None:
        """Mirrors page_crawl.yaml's shape: log, then navigate/wait/screenshot
        per page."""
        t = T0
        steps = [
            _log("step1", t),
            _navigate("step2", "http://localhost:8088/data/perspective/client/ToolboxAudit/", t),
            _wait("step3", t + timedelta(milliseconds=300)),
            _screenshot(
                "step4", "/data/screenshots/page_crawl_page1.webp", t + timedelta(milliseconds=310)
            ),
            _navigate(
                "step5",
                "http://localhost:8088/data/perspective/client/ToolboxAudit/page2",
                t + timedelta(milliseconds=400),
            ),
            _wait("step6", t + timedelta(milliseconds=650)),
            _screenshot(
                "step7", "/data/screenshots/page_crawl_page2.webp", t + timedelta(milliseconds=660)
            ),
        ]
        execution = _execution(steps)

        result = build_runtime_results_from_execution(execution)

        assert result.playbook_name == "perspective/page_crawl.yaml"
        assert len(result.pages) == 2
        assert result.all_pages_loaded_ok is True

        page1, page2 = result.pages
        assert page1.path == "/"
        assert page1.loaded_ok is True
        assert page1.load_time_ms == 300
        assert page1.screenshot_path == "/data/screenshots/page_crawl_page1.webp"
        assert page1.console_errors == []
        assert page1.error is None

        assert page2.path == "/page2"
        assert page2.load_time_ms == 250
        assert page2.screenshot_path == "/data/screenshots/page_crawl_page2.webp"

    def test_failed_wait_marks_page_not_loaded_ok(self) -> None:
        t = T0
        steps = [
            _navigate(
                "step1", "http://localhost:8088/data/perspective/client/ToolboxAudit/page2", t
            ),
            _wait(
                "step2",
                t + timedelta(seconds=30),
                status=StepStatus.FAILED,
                error="Timeout 30000ms exceeded waiting for selector",
            ),
        ]
        execution = _execution(steps, playbook_name="perspective/navigation_audit.yaml")

        result = build_runtime_results_from_execution(execution)

        assert len(result.pages) == 1
        page = result.pages[0]
        assert page.loaded_ok is False
        assert page.error == "Timeout 30000ms exceeded waiting for selector"
        assert page.load_time_ms is None  # never rendered, so no confirmed load time
        assert result.all_pages_loaded_ok is False

    def test_repeated_visits_to_same_path_produce_separate_entries(self) -> None:
        """navigation_audit.yaml visits Home twice (initial crawl + return to
        reach the nav button) - each visit should be its own entry, not
        deduplicated, since the report should reflect what actually ran."""
        t = T0
        home_url = "http://localhost:8088/data/perspective/client/ToolboxAudit/"
        steps = [
            _navigate("step1", home_url, t),
            _wait("step2", t + timedelta(milliseconds=200)),
            _navigate("step3", home_url, t + timedelta(seconds=1)),
            _wait("step4", t + timedelta(seconds=1, milliseconds=180)),
        ]
        execution = _execution(steps)

        result = build_runtime_results_from_execution(execution)

        assert [p.path for p in result.pages] == ["/", "/"]
        assert all(p.loaded_ok for p in result.pages)

    def test_button_click_navigation_is_its_own_correctly_attributed_entry(self) -> None:
        """Regression test mirroring navigation_audit.yaml's real shape: a
        browser.click drives an in-app (Perspective client-side) navigation
        with no intervening browser.navigate call. Without treating a
        path-changing perspective.verify_navigation as its own boundary,
        the post-click screenshot would be mis-attributed to the page the
        click navigated *away* from - this pins the fix."""
        home = "http://localhost:8088/data/perspective/client/ToolboxAudit/"
        page2 = "http://localhost:8088/data/perspective/client/ToolboxAudit/page2"
        t = T0

        steps = [
            # Return to Home (a plain browser.navigate + wait).
            _navigate("step10", home, t),
            _wait("step11", t + timedelta(milliseconds=300)),
            # Click the in-app nav button - no browser.navigate involved.
            _click("step12", t + timedelta(milliseconds=310)),
            _wait("step13", t + timedelta(milliseconds=600)),
            # Confirms the client-side route actually changed to /page2.
            _verify_navigation("step14", page2, "Page 2", t + timedelta(milliseconds=650)),
            _screenshot(
                "step16",
                "/data/screenshots/navigation_audit_button_click_page2.webp",
                t + timedelta(milliseconds=660),
            ),
        ]
        execution = _execution(steps, playbook_name="perspective/navigation_audit.yaml")

        result = build_runtime_results_from_execution(execution)

        assert [p.path for p in result.pages] == ["/", "/page2"]
        home_run, page2_run = result.pages
        assert home_run.screenshot_path is None  # no screenshot was taken before the click
        assert (
            page2_run.screenshot_path
            == "/data/screenshots/navigation_audit_button_click_page2.webp"
        )
        assert page2_run.loaded_ok is True

    def test_same_path_verify_navigation_is_not_a_boundary(self) -> None:
        """The common case: verify_navigation confirming a plain
        browser.navigate landed on the expected (same) path must not split
        one visit into two entries."""
        url = "http://localhost:8088/data/perspective/client/ToolboxAudit/page2"
        t = T0
        steps = [
            _navigate("step1", url, t),
            _wait("step2", t + timedelta(milliseconds=200)),
            _verify_navigation("step3", url, "Page 2", t + timedelta(milliseconds=220)),
            _screenshot("step4", "/data/screenshots/x.webp", t + timedelta(milliseconds=230)),
        ]
        execution = _execution(steps)

        result = build_runtime_results_from_execution(execution)

        assert len(result.pages) == 1
        assert result.pages[0].path == "/page2"
        assert result.pages[0].screenshot_path == "/data/screenshots/x.webp"
        assert (
            result.pages[0].load_time_ms == 200
        )  # from the browser.wait, not re-derived from verify_navigation

    def test_steps_before_first_navigate_are_ignored(self) -> None:
        steps = [_log("step1", T0)]
        execution = _execution(steps)

        result = build_runtime_results_from_execution(execution)

        assert result.pages == []
        assert result.all_pages_loaded_ok is True  # vacuously true

    def test_navigate_step_itself_failing_produces_no_page_entry(self) -> None:
        """Documented limitation: a failed browser.navigate has no output
        (StepExecutor only sets ``error`` on failure), so there is no URL to
        derive a page path from - the visit is skipped rather than reported
        with a fabricated empty path. The execution's own status/error is
        the source of truth for this case, not the page list."""
        steps = [
            _navigate(
                "step1",
                "http://localhost:8088/data/perspective/client/ToolboxAudit/",
                T0,
                status=StepStatus.FAILED,
            ),
        ]
        execution = _execution(steps)

        result = build_runtime_results_from_execution(execution)

        assert result.pages == []


class TestRuntimeAuditResultsToDict:
    def test_to_dict_shape(self) -> None:
        page = PageRuntimeResult(
            path="/",
            loaded_ok=True,
            load_time_ms=123.4,
            console_errors=[],
            screenshot_path="/tmp/x.webp",
        )
        results = RuntimeAuditResults(
            playbook_name="perspective/page_crawl.yaml",
            executed_at=T0,
            pages=[page],
        )

        data = results.to_dict()

        assert data["playbook_name"] == "perspective/page_crawl.yaml"
        assert data["executed_at"] == T0.isoformat()
        assert data["all_pages_loaded_ok"] is True
        assert data["pages"] == [
            {
                "path": "/",
                "loaded_ok": True,
                "load_time_ms": 123.4,
                "console_errors": [],
                "screenshot_path": "/tmp/x.webp",
                "error": None,
            }
        ]

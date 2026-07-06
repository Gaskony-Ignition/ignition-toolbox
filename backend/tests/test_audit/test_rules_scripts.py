"""Tests for InvokeAsynchronousDaemonRule and ClickHandlerVsNativeNavRule."""

from ignition_toolkit.audit.rules.perspective.scripts import (
    ClickHandlerVsNativeNavRule,
    InvokeAsynchronousDaemonRule,
)

from .conftest import load_project


def test_invoke_asynchronous_fires_on_daemon_start() -> None:
    project = load_project("rules/invoke_async/positive")

    findings = InvokeAsynchronousDaemonRule().evaluate(project)

    assert len(findings) == 1
    assert findings[0].rule_id == "scripts-invoke-asynchronous-daemon"
    assert findings[0].location == "View > root"


def test_invoke_asynchronous_silent_on_ordinary_startup_script() -> None:
    project = load_project("rules/invoke_async/negative")

    findings = InvokeAsynchronousDaemonRule().evaluate(project)

    assert findings == []


def test_click_handler_vs_native_nav_fires_on_script_navigate() -> None:
    project = load_project("rules/click_nav/positive")

    findings = ClickHandlerVsNativeNavRule().evaluate(project)

    assert len(findings) == 1
    assert findings[0].rule_id == "scripts-click-handler-vs-native-nav"
    assert findings[0].location == "View > root/AlarmIcon"


def test_click_handler_vs_native_nav_silent_on_native_nav_action() -> None:
    project = load_project("rules/click_nav/negative")

    findings = ClickHandlerVsNativeNavRule().evaluate(project)

    assert findings == []

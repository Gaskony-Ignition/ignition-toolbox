"""Regression test against a real gateway view.json (fixtures/real/), copied
verbatim from /home/nigel/claude/ignition/home/project_mirror/Navigation/Header
(no personal data in the file — verified before copying). This view is real
production Perspective content, not a hand-crafted example, and exercises
several rules at once against genuine gateway output:

- the "Alarms" component polls every 2 seconds via now(2000) -> fast-polling
- the "Date" label hardcodes color: "#FFFFFF" -> hardcoded-color
- every clickable component uses a native nav/dock/toggle action, never a
  script that calls system.perspective.navigate -> click-handler rule silent
"""

from ignition_toolkit.audit.rules.perspective.bindings import FastPollingRule
from ignition_toolkit.audit.rules.perspective.consistency import HardcodedColorRule
from ignition_toolkit.audit.rules.perspective.scripts import ClickHandlerVsNativeNavRule

from .conftest import load_project


def test_real_header_view_flags_known_fast_polling_smell() -> None:
    project = load_project("real")

    findings = FastPollingRule().evaluate(project)

    assert len(findings) == 1
    assert "2000 ms" in findings[0].message
    assert findings[0].location.startswith("Navigation/Header > root/Alarms")


def test_real_header_view_flags_known_hardcoded_color_smell() -> None:
    project = load_project("real")

    findings = HardcodedColorRule().evaluate(project)

    assert len(findings) == 1
    assert "#FFFFFF" in findings[0].message
    assert findings[0].location == "Navigation/Header > root/Date"


def test_real_header_view_uses_native_nav_not_script_click_handlers() -> None:
    """The real Header view does navigation correctly (native nav/dock actions) —
    this rule should stay completely silent on it."""
    project = load_project("real")

    findings = ClickHandlerVsNativeNavRule().evaluate(project)

    assert findings == []

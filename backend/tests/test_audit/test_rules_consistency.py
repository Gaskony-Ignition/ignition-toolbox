"""Tests for HardcodedColorRule."""

from ignition_toolkit.audit.rules.perspective.consistency import HardcodedColorRule

from .conftest import load_project


def test_fires_on_literal_hex_color() -> None:
    project = load_project("rules/hardcoded_color/positive")

    findings = HardcodedColorRule().evaluate(project)

    assert len(findings) == 1
    assert findings[0].rule_id == "consistency-hardcoded-color"
    assert findings[0].location == "View > root/Date"
    assert "#FFFFFF" in findings[0].message


def test_silent_on_theme_variable() -> None:
    project = load_project("rules/hardcoded_color/negative")

    findings = HardcodedColorRule().evaluate(project)

    assert findings == []

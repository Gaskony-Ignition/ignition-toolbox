"""Tests for CoordContainerOveruseRule and MissingMinSizeRule."""

from ignition_toolkit.audit.rules.perspective.layout import (
    CoordContainerOveruseRule,
    MissingMinSizeRule,
)

from .conftest import load_project


def test_coord_container_fires_on_unnamed_overlay() -> None:
    project = load_project("rules/coord_container/positive")

    findings = CoordContainerOveruseRule().evaluate(project)

    assert len(findings) == 1
    assert findings[0].location == "View > root/Overlay"
    assert findings[0].rule_id == "layout-coord-container-overuse"


def test_coord_container_silent_on_diagram_name() -> None:
    project = load_project("rules/coord_container/negative")

    findings = CoordContainerOveruseRule().evaluate(project)

    assert findings == []


def test_missing_min_size_fires_when_style_omits_min_size() -> None:
    project = load_project("rules/min_size/positive")

    findings = MissingMinSizeRule().evaluate(project)

    assert len(findings) == 1
    assert findings[0].location == "View > root/Card"
    assert findings[0].rule_id == "layout-missing-min-size"


def test_missing_min_size_silent_when_min_size_set() -> None:
    project = load_project("rules/min_size/negative")

    findings = MissingMinSizeRule().evaluate(project)

    assert findings == []

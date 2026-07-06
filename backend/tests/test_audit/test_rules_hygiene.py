"""Tests for OversizedEmbeddedImageRule and UnreachableViewRule."""

from ignition_toolkit.audit.rules.perspective.hygiene import (
    OversizedEmbeddedImageRule,
    UnreachableViewRule,
)

from .conftest import load_project


def test_oversized_image_fires_over_threshold() -> None:
    project = load_project("rules/oversized_image/positive")

    findings = OversizedEmbeddedImageRule().evaluate(project)

    assert len(findings) == 1
    assert findings[0].rule_id == "hygiene-oversized-embedded-image"
    assert findings[0].location == "View > root/71oUI5FZdKL._SL1500_"


def test_oversized_image_silent_under_threshold() -> None:
    project = load_project("rules/oversized_image/negative")

    findings = OversizedEmbeddedImageRule().evaluate(project)

    assert findings == []


def test_unreachable_view_fires_on_orphan_view() -> None:
    project = load_project("rules/unreachable_view/positive")

    findings = UnreachableViewRule().evaluate(project)

    assert len(findings) == 1
    assert findings[0].rule_id == "hygiene-unreachable-view"
    assert findings[0].location == "Orphan"


def test_unreachable_view_silent_when_all_views_reachable() -> None:
    project = load_project("rules/unreachable_view/negative")

    findings = UnreachableViewRule().evaluate(project)

    assert findings == []

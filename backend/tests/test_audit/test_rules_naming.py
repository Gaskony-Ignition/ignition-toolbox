"""Tests for NamingMeaninglessNameRule (fixtures: rules/naming/{positive,negative})."""

from ignition_toolkit.audit.rules.perspective.naming import NamingMeaninglessNameRule

from .conftest import load_project


def test_fires_on_default_and_filename_derived_names() -> None:
    project = load_project("rules/naming/positive")

    findings = NamingMeaninglessNameRule().evaluate(project)

    assert len(findings) == 2
    assert all(f.rule_id == "naming-meaningless-name" for f in findings)
    flagged_locations = {f.location for f in findings}
    assert "View > root/Label_1" in flagged_locations
    assert "View > root/71oUI5FZdKL._SL1500_" in flagged_locations


def test_silent_on_descriptive_names() -> None:
    project = load_project("rules/naming/negative")

    findings = NamingMeaninglessNameRule().evaluate(project)

    assert findings == []


def test_view_root_component_named_root_is_never_flagged() -> None:
    """Every view's root component is conventionally named "root" — not a smell."""
    project = load_project("rules/naming/negative")

    findings = NamingMeaninglessNameRule().evaluate(project)

    assert not any(f.location.endswith("> root") for f in findings)

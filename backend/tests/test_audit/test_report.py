"""Tests for report.py — aggregation logic and markdown/dict rendering.

Most tests build a synthetic findings list directly (mirrors test_engine.py's
approach of not depending on PerspectiveProject) since aggregation only
cares about Finding.rule_id/severity/location. One test runs the full
pipeline (engine -> report) against the real mini_project fixture to prove
the pieces fit together end to end.
"""

from ignition_toolkit.audit.engine import Finding, RuleEngine, Severity
from ignition_toolkit.audit.project import Inventory
from ignition_toolkit.audit.report import (
    AuditReport,
    aggregate_findings,
    generate_report,
    rule_family_counts,
    severity_counts,
)
from ignition_toolkit.audit.rules.perspective import default_rules

from .conftest import load_project


def _finding(
    rule_id: str = "consistency-hardcoded-color",
    severity: Severity = Severity.INFO,
    location: str = "Home > root/Label",
    message: str = "msg",
    recommendation: str = "rec",
) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,
        location=location,
        message=message,
        recommendation=recommendation,
    )


EMPTY_INVENTORY = Inventory(
    view_count=0, component_count=0, component_count_by_type={}, binding_count=0, views=[]
)


class TestAggregateFindings:
    def test_groups_same_rule_same_view_into_one_row(self) -> None:
        """The motivating case: 261 hardcoded-color findings in one view must
        collapse to a single aggregated row, not 261 report rows."""
        findings = [_finding(location=f"Home > root/Label_{i}") for i in range(261)]

        aggregated = aggregate_findings(findings)

        assert len(aggregated) == 1
        assert aggregated[0].count == 261
        assert aggregated[0].view == "Home"

    def test_caps_example_locations_at_three(self) -> None:
        findings = [_finding(location=f"Home > root/Label_{i}") for i in range(10)]

        aggregated = aggregate_findings(findings)

        assert len(aggregated[0].example_locations) == 3

    def test_different_views_produce_separate_rows(self) -> None:
        findings = [
            _finding(location="Home > root/Label"),
            _finding(location="Popup/Confirm > root/Label"),
        ]

        aggregated = aggregate_findings(findings)

        assert {a.view for a in aggregated} == {"Home", "Popup/Confirm"}
        assert all(a.count == 1 for a in aggregated)

    def test_different_rules_same_view_produce_separate_rows(self) -> None:
        findings = [
            _finding(rule_id="consistency-hardcoded-color", location="Home > root/Label"),
            _finding(rule_id="naming-meaningless-name", location="Home > root/Label"),
        ]

        aggregated = aggregate_findings(findings)

        assert len(aggregated) == 2
        assert {a.rule_id for a in aggregated} == {
            "consistency-hardcoded-color",
            "naming-meaningless-name",
        }

    def test_view_level_finding_without_component_path_groups_correctly(self) -> None:
        """hygiene-unreachable-view findings use a bare view path as location
        (no " > component" suffix) — must still group sanely."""
        findings = [
            _finding(
                rule_id="hygiene-unreachable-view",
                location="Orphan/View",
                message="m",
                recommendation="r",
            ),
        ]

        aggregated = aggregate_findings(findings)

        assert len(aggregated) == 1
        assert aggregated[0].view == "Orphan/View"
        assert aggregated[0].example_locations == ["Orphan/View"]

    def test_sorted_by_severity_then_count_descending(self) -> None:
        findings = [
            _finding(rule_id="info-rule", severity=Severity.INFO, location="A > root/X"),
            _finding(rule_id="critical-rule", severity=Severity.CRITICAL, location="B > root/X"),
            _finding(rule_id="high-rule-a", severity=Severity.HIGH, location="C > root/X"),
            _finding(rule_id="high-rule-b", severity=Severity.HIGH, location="D > root/X"),
            _finding(rule_id="high-rule-b", severity=Severity.HIGH, location="D > root/Y"),
        ]

        aggregated = aggregate_findings(findings)

        assert aggregated[0].severity == Severity.CRITICAL
        # Both HIGH rows come before the INFO row, and the higher-count HIGH
        # row (high-rule-b, count 2) sorts ahead of the count-1 HIGH row.
        assert aggregated[1].rule_id == "high-rule-b"
        assert aggregated[1].count == 2
        assert aggregated[2].rule_id == "high-rule-a"
        assert aggregated[-1].severity == Severity.INFO

    def test_multi_occurrence_recommendation_notes_the_count(self) -> None:
        findings = [
            _finding(location=f"Home > root/Label_{i}", recommendation="Fix it.") for i in range(5)
        ]

        aggregated = aggregate_findings(findings)

        assert "5 occurrences" in aggregated[0].recommendation
        assert aggregated[0].recommendation.startswith("Fix it.")


class TestSummaryCounts:
    def test_severity_counts_are_zero_filled(self) -> None:
        counts = severity_counts([_finding(severity=Severity.CRITICAL)])

        assert counts == {"critical": 1, "high": 0, "medium": 0, "info": 0}

    def test_rule_family_counts_group_by_prefix(self) -> None:
        findings = [
            _finding(rule_id="naming-meaningless-name"),
            _finding(rule_id="naming-something-else"),
            _finding(rule_id="consistency-hardcoded-color"),
        ]

        counts = rule_family_counts(findings)

        assert counts == {"consistency": 1, "naming": 2}


class TestAuditReportToDict:
    def test_to_dict_carries_both_aggregated_and_full_findings(self) -> None:
        findings = [_finding(location=f"Home > root/Label_{i}") for i in range(5)]
        report = generate_report("MyProject", EMPTY_INVENTORY, findings)

        data = report.to_dict()

        assert data["project_name"] == "MyProject"
        assert data["summary"]["total_findings"] == 5
        assert len(data["aggregated_findings"]) == 1
        assert data["aggregated_findings"][0]["count"] == 5
        assert len(data["findings"]) == 5

    def test_to_dict_handles_no_findings(self) -> None:
        report = generate_report("Clean", EMPTY_INVENTORY, [])

        data = report.to_dict()

        assert data["summary"]["total_findings"] == 0
        assert data["aggregated_findings"] == []
        assert data["findings"] == []


class TestAuditReportToMarkdown:
    def test_markdown_includes_executive_summary_and_view_sections(self) -> None:
        findings = [_finding(location=f"Home > root/Label_{i}") for i in range(261)]
        report = generate_report("MyProject", EMPTY_INVENTORY, findings)

        markdown = report.to_markdown()

        assert "# Perspective Project Audit Report — MyProject" in markdown
        assert "## Executive Summary" in markdown
        assert "## Findings by View" in markdown
        assert "## Remediation Appendix" in markdown
        # The 261 findings must appear as one aggregated row, not 261 lines.
        assert "| consistency-hardcoded-color | Info | 261 |" in markdown

    def test_markdown_with_no_findings_says_so(self) -> None:
        report = generate_report("Clean", EMPTY_INVENTORY, [])

        markdown = report.to_markdown()

        assert "No findings" in markdown

    def test_markdown_is_deterministic_given_fixed_generated_at(self) -> None:
        from datetime import UTC, datetime

        fixed_time = datetime(2026, 7, 4, 12, 0, tzinfo=UTC)
        findings = [_finding()]

        report_a = AuditReport("P", EMPTY_INVENTORY, findings, generated_at=fixed_time)
        report_b = AuditReport("P", EMPTY_INVENTORY, findings, generated_at=fixed_time)

        assert report_a.to_markdown() == report_b.to_markdown()


class TestRealFixturePipeline:
    def test_full_pipeline_on_mini_project_fixture(self) -> None:
        """Loader -> engine -> report, end to end, against the hand-built
        mini_project fixture used by test_project.py."""
        project = load_project("mini_project")
        findings = RuleEngine(default_rules()).run(project)

        report = generate_report(project.name, project.inventory(), findings)
        data = report.to_dict()

        assert data["project_name"] == "mini_project"
        assert data["inventory"]["component_count"] == 5
        # Whatever the seed rules find, the aggregated count must reconcile
        # exactly with the full findings list (no findings lost or invented
        # during aggregation).
        assert sum(a["count"] for a in data["aggregated_findings"]) == len(data["findings"])

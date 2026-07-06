"""
Perspective audit report rendering.

Turns a flat ``list[Finding]`` (as produced by :class:`ignition_toolkit.audit.engine.RuleEngine`)
plus a project :class:`~ignition_toolkit.audit.project.Inventory` into a
customer-facing report, in two forms:

- :meth:`AuditReport.to_dict` — a structured dict for the API response
  (executive summary counts, findings *aggregated* by rule+view, and the
  full flat findings list for anyone who wants the raw detail).
- :meth:`AuditReport.to_markdown` — the same content rendered as a
  markdown document suitable for handing to a customer.

Aggregation is not optional polish here: a real gateway project audited
during Phase 2 produced 261 separate ``consistency-hardcoded-color``
findings in a single view. A raw findings table at that scale is not a
usable customer deliverable — the report groups same-rule-same-view
findings into one row (count + up to 3 example locations) everywhere
except the full findings list carried alongside it for completeness.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ignition_toolkit.audit.engine import Finding, Severity
from ignition_toolkit.audit.project import Inventory

logger = logging.getLogger(__name__)

# Only used to order the executive summary / markdown tables from most to
# least urgent — matches declaration order in Severity, kept explicit so a
# future reordering of the enum doesn't silently reorder the report.
_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.INFO: 3,
}

# Max example locations shown per aggregated (rule, view) row.
_MAX_EXAMPLES = 3


def _view_of(location: str) -> str:
    """Extract the view path from a ``Finding.location`` string.

    Component-level findings use ``"<view path> > <component path>"``;
    view-level findings (e.g. ``hygiene-unreachable-view``) use the bare
    view path. Splitting on the first ``" > "`` handles both uniformly.
    """
    return location.split(" > ", 1)[0]


def _rule_family(rule_id: str) -> str:
    """The rule family prefix of a rule id, e.g. ``"naming"`` from ``"naming-meaningless-name"``."""
    return rule_id.split("-", 1)[0]


@dataclass(frozen=True)
class AggregatedFinding:
    """One (rule, view) group of findings, collapsed to a single report row."""

    rule_id: str
    severity: Severity
    view: str
    count: int
    example_locations: list[str]
    message: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "view": self.view,
            "count": self.count,
            "example_locations": self.example_locations,
            "message": self.message,
            "recommendation": self.recommendation,
        }


def aggregate_findings(findings: list[Finding]) -> list[AggregatedFinding]:
    """Group findings by (rule_id, view), sorted by severity then count desc.

    Each group keeps up to :data:`_MAX_EXAMPLES` example locations. The
    representative message/recommendation come from the first finding in
    the group; for groups of more than one, a note is appended to the
    recommendation pointing at the example locations rather than repeating
    the (often instance-specific) recommendation text once per occurrence.
    """
    groups: dict[tuple[str, str], list[Finding]] = defaultdict(list)
    for finding in findings:
        groups[(finding.rule_id, _view_of(finding.location))].append(finding)

    aggregated: list[AggregatedFinding] = []
    for (rule_id, view), group in groups.items():
        count = len(group)
        representative = group[0]
        recommendation = representative.recommendation
        if count > 1:
            recommendation = (
                f"{recommendation} ({count} occurrences of this issue were found in "
                f"{view}; the same fix applies to each — see example locations.)"
            )
        message = (
            representative.message
            if count == 1
            else f"{count} components in {view} trigger this rule."
        )
        aggregated.append(
            AggregatedFinding(
                rule_id=rule_id,
                severity=representative.severity,
                view=view,
                count=count,
                example_locations=[f.location for f in group[:_MAX_EXAMPLES]],
                message=message,
                recommendation=recommendation,
            )
        )

    return sorted(
        aggregated,
        key=lambda a: (_SEVERITY_ORDER[a.severity], -a.count, a.rule_id, a.view),
    )


def severity_counts(findings: list[Finding]) -> dict[str, int]:
    """Count of findings per severity, zero-filled for severities with no findings."""
    counts = {severity.value: 0 for severity in Severity}
    for finding in findings:
        counts[finding.severity.value] += 1
    return counts


def rule_family_counts(findings: list[Finding]) -> dict[str, int]:
    """Count of findings per rule family (the prefix before the first ``-``)."""
    counts: dict[str, int] = defaultdict(int)
    for finding in findings:
        counts[_rule_family(finding.rule_id)] += 1
    return dict(sorted(counts.items()))


@dataclass
class AuditReport:
    """A complete audit report: inventory, aggregated findings, and full detail.

    Build via :func:`generate_report`; render via :meth:`to_dict` (API) or
    :meth:`to_markdown` (customer-facing document).
    """

    project_name: str
    inventory: Inventory
    findings: list[Finding]
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def aggregated(self) -> list[AggregatedFinding]:
        return aggregate_findings(self.findings)

    def to_dict(self) -> dict[str, Any]:
        """Structured report for the API response.

        Carries both the aggregated view (what a customer report should
        show) and the full flat findings list (for anyone who needs the
        raw detail, e.g. a future CSV export).
        """
        findings = self.findings
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at.isoformat(),
            "inventory": {
                "view_count": self.inventory.view_count,
                "component_count": self.inventory.component_count,
                "component_count_by_type": self.inventory.component_count_by_type,
                "binding_count": self.inventory.binding_count,
                "views": self.inventory.views,
            },
            "summary": {
                "total_findings": len(findings),
                "by_severity": severity_counts(findings),
                "by_rule_family": rule_family_counts(findings),
            },
            "aggregated_findings": [a.to_dict() for a in self.aggregated],
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity.value,
                    "location": f.location,
                    "message": f.message,
                    "recommendation": f.recommendation,
                }
                for f in findings
            ],
        }

    def to_markdown(self) -> str:
        """Render the customer-facing markdown report.

        Sections: executive summary (counts per severity and rule family),
        findings grouped by view (aggregated rows), and a remediation
        appendix (one entry per rule id, across the whole project).
        """
        lines: list[str] = []
        findings = self.findings
        aggregated = self.aggregated

        lines.append(f"# Perspective Project Audit Report — {self.project_name}")
        lines.append("")
        lines.append(f"*Generated {self.generated_at.strftime('%d/%m/%Y %H:%M UTC')}*")
        lines.append("")

        # --- Executive summary ------------------------------------------------
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(
            f"This project has **{self.inventory.view_count} views**, "
            f"**{self.inventory.component_count} components**, and "
            f"**{self.inventory.binding_count} bindings**. The audit raised "
            f"**{len(findings)} findings** across {len(aggregated)} distinct "
            "rule/view combinations."
        )
        lines.append("")

        lines.append("### Findings by severity")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("| --- | --- |")
        counts_by_severity = severity_counts(findings)
        for severity in sorted(Severity, key=lambda s: _SEVERITY_ORDER[s]):
            lines.append(
                f"| {severity.value.capitalize()} | {counts_by_severity[severity.value]} |"
            )
        lines.append("")

        lines.append("### Findings by rule family")
        lines.append("")
        lines.append("| Rule family | Count |")
        lines.append("| --- | --- |")
        for family, count in rule_family_counts(findings).items():
            lines.append(f"| {family.capitalize()} | {count} |")
        lines.append("")

        # --- Findings by view ---------------------------------------------------
        lines.append("## Findings by View")
        lines.append("")
        if not aggregated:
            lines.append("No findings — nothing to report.")
            lines.append("")
        else:
            by_view: dict[str, list[AggregatedFinding]] = defaultdict(list)
            for row in aggregated:
                by_view[row.view].append(row)

            for view in sorted(by_view, key=lambda v: (-len(by_view[v]), v)):
                rows = by_view[view]
                total = sum(r.count for r in rows)
                lines.append(f"### {view} ({total} finding{'s' if total != 1 else ''})")
                lines.append("")
                lines.append("| Rule | Severity | Count | Example locations |")
                lines.append("| --- | --- | --- | --- |")
                for row in sorted(rows, key=lambda r: (_SEVERITY_ORDER[r.severity], -r.count)):
                    examples = "; ".join(row.example_locations)
                    lines.append(
                        f"| {row.rule_id} | {row.severity.value.capitalize()} | {row.count} | {examples} |"
                    )
                lines.append("")

        # --- Remediation appendix ------------------------------------------------
        lines.append("## Remediation Appendix")
        lines.append("")
        if not findings:
            lines.append("No findings — nothing to remediate.")
            lines.append("")
        else:
            by_rule: dict[str, list[Finding]] = defaultdict(list)
            for finding in findings:
                by_rule[finding.rule_id].append(finding)

            for rule_id in sorted(
                by_rule, key=lambda r: (_SEVERITY_ORDER[by_rule[r][0].severity], r)
            ):
                rule_findings = by_rule[rule_id]
                severity = rule_findings[0].severity
                views = sorted({_view_of(f.location) for f in rule_findings})
                lines.append(f"### {rule_id} ({severity.value.capitalize()})")
                lines.append("")
                lines.append(
                    f"Found {len(rule_findings)} time(s) across {len(views)} "
                    f"view(s): {', '.join(views)}."
                )
                lines.append("")
                lines.append(rule_findings[0].recommendation)
                lines.append("")

        return "\n".join(lines)


def generate_report(
    project_name: str,
    inventory: Inventory,
    findings: list[Finding],
    generated_at: datetime | None = None,
) -> AuditReport:
    """Build an :class:`AuditReport` from a project's inventory and findings."""
    return AuditReport(
        project_name=project_name,
        inventory=inventory,
        findings=list(findings),
        generated_at=generated_at or datetime.now(UTC),
    )

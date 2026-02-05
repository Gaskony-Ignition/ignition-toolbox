"""
Report Exporter

Exports reports to various formats (CSV, JSON).
"""

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ignition_toolkit.reporting.reports import Report

logger = logging.getLogger(__name__)


class ReportExporter:
    """
    Report Exporter

    Exports reports to various formats:
    - JSON (full report data)
    - CSV (tabular execution data)

    Example:
        exporter = ReportExporter()

        # Export to JSON
        json_data = exporter.to_json(report)

        # Export to CSV
        csv_data = exporter.to_csv(report)

        # Save to file
        exporter.save_json(report, Path("/path/to/report.json"))
        exporter.save_csv(report, Path("/path/to/report.csv"))
    """

    def to_json(self, report: Report, indent: int = 2) -> str:
        """
        Export report to JSON string

        Args:
            report: Report to export
            indent: JSON indentation (0 for compact)

        Returns:
            JSON string
        """
        return json.dumps(
            report.to_dict(),
            indent=indent if indent > 0 else None,
            default=self._json_serializer,
        )

    def to_csv(
        self,
        report: Report,
        include_summary: bool = True,
        include_executions: bool = True,
        include_playbook_stats: bool = True,
    ) -> str:
        """
        Export report to CSV string

        Creates a multi-section CSV with:
        - Summary statistics
        - Execution details
        - Playbook statistics

        Args:
            report: Report to export
            include_summary: Include summary section
            include_executions: Include executions section
            include_playbook_stats: Include playbook stats section

        Returns:
            CSV string
        """
        output = io.StringIO()

        # Summary section
        if include_summary and report.overall_stats:
            output.write("# Summary Statistics\n")
            writer = csv.writer(output)
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Report Title", report.title])
            writer.writerow(["Generated At", report.generated_at.isoformat()])
            writer.writerow(["Period Start", report.period_start.isoformat() if report.period_start else "N/A"])
            writer.writerow(["Period End", report.period_end.isoformat() if report.period_end else "N/A"])
            writer.writerow(["Total Executions", report.overall_stats.total_executions])
            writer.writerow(["Passed", report.overall_stats.passed])
            writer.writerow(["Failed", report.overall_stats.failed])
            writer.writerow(["Running", report.overall_stats.running])
            writer.writerow(["Cancelled", report.overall_stats.cancelled])
            writer.writerow(["Pass Rate", f"{report.overall_stats.pass_rate:.2%}"])
            writer.writerow(["Avg Duration (s)", f"{report.overall_stats.avg_duration_seconds:.2f}"])
            writer.writerow(["Min Duration (s)", f"{report.overall_stats.min_duration_seconds:.2f}" if report.overall_stats.min_duration_seconds else "N/A"])
            writer.writerow(["Max Duration (s)", f"{report.overall_stats.max_duration_seconds:.2f}" if report.overall_stats.max_duration_seconds else "N/A"])
            writer.writerow(["Total Steps", report.overall_stats.total_steps])
            writer.writerow(["Steps Passed", report.overall_stats.steps_passed])
            writer.writerow(["Steps Failed", report.overall_stats.steps_failed])
            output.write("\n")

        # Executions section
        if include_executions and report.executions:
            output.write("# Execution Details\n")
            writer = csv.writer(output)
            writer.writerow([
                "ID",
                "Playbook",
                "Status",
                "Started At",
                "Completed At",
                "Duration (s)",
                "Total Steps",
                "Passed Steps",
                "Failed Steps",
                "Error Message",
            ])

            for exec in report.executions:
                writer.writerow([
                    exec.id,
                    exec.playbook_name,
                    exec.status,
                    exec.started_at.isoformat() if exec.started_at else "",
                    exec.completed_at.isoformat() if exec.completed_at else "",
                    f"{exec.duration_seconds:.2f}" if exec.duration_seconds else "",
                    exec.total_steps,
                    exec.passed_steps,
                    exec.failed_steps,
                    exec.error_message or "",
                ])
            output.write("\n")

        # Playbook stats section
        if include_playbook_stats and report.playbook_stats:
            output.write("# Playbook Statistics\n")
            writer = csv.writer(output)
            writer.writerow([
                "Playbook",
                "Path",
                "Total Executions",
                "Passed",
                "Failed",
                "Pass Rate",
                "Avg Duration (s)",
                "Last Execution",
                "Last Status",
            ])

            for stats in report.playbook_stats:
                writer.writerow([
                    stats.playbook_name,
                    stats.playbook_path,
                    stats.total_executions,
                    stats.passed,
                    stats.failed,
                    f"{stats.pass_rate:.2%}",
                    f"{stats.avg_duration_seconds:.2f}",
                    stats.last_execution.isoformat() if stats.last_execution else "",
                    stats.last_status or "",
                ])
            output.write("\n")

        # Trends section
        if report.trends:
            output.write("# Pass/Fail Trends\n")
            writer = csv.writer(output)
            writer.writerow(["Date", "Total", "Passed", "Failed", "Pass Rate"])

            for trend in report.trends:
                writer.writerow([
                    trend.date,
                    trend.total,
                    trend.passed,
                    trend.failed,
                    f"{trend.pass_rate:.2%}",
                ])
            output.write("\n")

        return output.getvalue()

    def to_executions_csv(self, report: Report) -> str:
        """
        Export only executions to a simple CSV

        Args:
            report: Report to export

        Returns:
            CSV string with execution data only
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "ID",
            "Playbook Path",
            "Playbook Name",
            "Status",
            "Started At",
            "Completed At",
            "Duration (seconds)",
            "Total Steps",
            "Passed Steps",
            "Failed Steps",
            "Error Message",
        ])

        for exec in report.executions:
            writer.writerow([
                exec.id,
                exec.playbook_path,
                exec.playbook_name,
                exec.status,
                exec.started_at.isoformat() if exec.started_at else "",
                exec.completed_at.isoformat() if exec.completed_at else "",
                exec.duration_seconds if exec.duration_seconds else "",
                exec.total_steps,
                exec.passed_steps,
                exec.failed_steps,
                exec.error_message or "",
            ])

        return output.getvalue()

    def save_json(self, report: Report, path: Path, indent: int = 2) -> None:
        """
        Save report as JSON file

        Args:
            report: Report to save
            path: Output file path
            indent: JSON indentation
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        json_data = self.to_json(report, indent=indent)
        path.write_text(json_data, encoding="utf-8")
        logger.info(f"Saved JSON report to {path}")

    def save_csv(self, report: Report, path: Path) -> None:
        """
        Save report as CSV file

        Args:
            report: Report to save
            path: Output file path
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        csv_data = self.to_csv(report)
        path.write_text(csv_data, encoding="utf-8")
        logger.info(f"Saved CSV report to {path}")

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-standard types"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# Global instance
_exporter: ReportExporter | None = None


def get_report_exporter() -> ReportExporter:
    """Get the global report exporter instance"""
    global _exporter
    if _exporter is None:
        _exporter = ReportExporter()
    return _exporter

"""
Report Generator

Creates formatted reports from execution data.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from ignition_toolkit.reporting.analytics import (
    ExecutionAnalytics,
    ExecutionStats,
    PlaybookStats,
    TrendPoint,
    get_execution_analytics,
)
from ignition_toolkit.storage.database import get_database

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDetail:
    """Detailed execution information"""
    id: int
    playbook_path: str
    playbook_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    total_steps: int
    passed_steps: int
    failed_steps: int
    error_message: str | None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class Report:
    """Generated report"""
    title: str
    generated_at: datetime
    period_start: datetime | None
    period_end: datetime | None
    overall_stats: ExecutionStats | None = None
    trends: list[TrendPoint] = field(default_factory=list)
    playbook_stats: list[PlaybookStats] = field(default_factory=list)
    executions: list[ExecutionDetail] = field(default_factory=list)
    failure_analysis: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary"""
        return {
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "overall_stats": {
                "total_executions": self.overall_stats.total_executions,
                "passed": self.overall_stats.passed,
                "failed": self.overall_stats.failed,
                "running": self.overall_stats.running,
                "cancelled": self.overall_stats.cancelled,
                "pass_rate": self.overall_stats.pass_rate,
                "avg_duration_seconds": self.overall_stats.avg_duration_seconds,
                "min_duration_seconds": self.overall_stats.min_duration_seconds,
                "max_duration_seconds": self.overall_stats.max_duration_seconds,
                "total_steps": self.overall_stats.total_steps,
                "steps_passed": self.overall_stats.steps_passed,
                "steps_failed": self.overall_stats.steps_failed,
            } if self.overall_stats else None,
            "trends": [
                {
                    "date": t.date,
                    "total": t.total,
                    "passed": t.passed,
                    "failed": t.failed,
                    "pass_rate": t.pass_rate,
                }
                for t in self.trends
            ],
            "playbook_stats": [
                {
                    "playbook_path": p.playbook_path,
                    "playbook_name": p.playbook_name,
                    "total_executions": p.total_executions,
                    "passed": p.passed,
                    "failed": p.failed,
                    "pass_rate": p.pass_rate,
                    "avg_duration_seconds": p.avg_duration_seconds,
                    "last_execution": p.last_execution.isoformat() if p.last_execution else None,
                    "last_status": p.last_status,
                }
                for p in self.playbook_stats
            ],
            "executions": [
                {
                    "id": e.id,
                    "playbook_path": e.playbook_path,
                    "playbook_name": e.playbook_name,
                    "status": e.status,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    "duration_seconds": e.duration_seconds,
                    "total_steps": e.total_steps,
                    "passed_steps": e.passed_steps,
                    "failed_steps": e.failed_steps,
                    "error_message": e.error_message,
                    "parameters": e.parameters,
                }
                for e in self.executions
            ],
            "failure_analysis": self.failure_analysis,
            "metadata": self.metadata,
        }


class ReportGenerator:
    """
    Report Generator

    Creates comprehensive reports from execution history:
    - Summary reports with overall statistics
    - Trend reports showing pass/fail over time
    - Detailed execution reports
    - Playbook performance reports

    Example:
        generator = ReportGenerator()

        # Generate summary report for last 30 days
        report = generator.generate_summary_report(days=30)

        # Generate detailed report for specific playbook
        report = generator.generate_playbook_report("my_playbook.yaml")
    """

    def __init__(self):
        self.analytics = get_execution_analytics()
        self.db = get_database()

    def generate_summary_report(
        self,
        days: int = 30,
        include_trends: bool = True,
        include_playbook_stats: bool = True,
        include_failure_analysis: bool = True,
        trend_granularity: str = "day",
    ) -> Report:
        """
        Generate a summary report

        Args:
            days: Number of days to include
            include_trends: Include trend data
            include_playbook_stats: Include per-playbook statistics
            include_failure_analysis: Include failure pattern analysis
            trend_granularity: "day", "week", or "month"

        Returns:
            Generated Report object
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        report = Report(
            title=f"Execution Summary Report ({days} days)",
            generated_at=datetime.now(UTC),
            period_start=start_time,
            period_end=end_time,
            metadata={
                "report_type": "summary",
                "days": days,
                "trend_granularity": trend_granularity,
            },
        )

        # Get overall stats
        report.overall_stats = self.analytics.get_overall_stats(
            start_time=start_time,
            end_time=end_time,
        )

        # Get trends
        if include_trends:
            report.trends = self.analytics.get_pass_fail_trends(
                days=days,
                granularity=trend_granularity,
            )

        # Get playbook stats
        if include_playbook_stats:
            report.playbook_stats = self.analytics.get_playbook_stats(
                start_time=start_time,
                end_time=end_time,
            )

        # Get failure analysis
        if include_failure_analysis:
            report.failure_analysis = self.analytics.get_failure_analysis(days=days)

        logger.info(f"Generated summary report: {report.overall_stats.total_executions} executions")
        return report

    def generate_playbook_report(
        self,
        playbook_path: str,
        days: int = 30,
        include_executions: bool = True,
        execution_limit: int = 100,
    ) -> Report:
        """
        Generate a report for a specific playbook

        Args:
            playbook_path: Path to the playbook
            days: Number of days to include
            include_executions: Include detailed execution list
            execution_limit: Maximum executions to include

        Returns:
            Generated Report object
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        playbook_name = playbook_path.split("/")[-1] if playbook_path else "Unknown"

        report = Report(
            title=f"Playbook Report: {playbook_name}",
            generated_at=datetime.now(UTC),
            period_start=start_time,
            period_end=end_time,
            metadata={
                "report_type": "playbook",
                "playbook_path": playbook_path,
                "days": days,
            },
        )

        # Get stats for this playbook
        report.overall_stats = self.analytics.get_overall_stats(
            start_time=start_time,
            end_time=end_time,
            playbook_path=playbook_path,
        )

        # Get trends for this playbook
        report.trends = self.analytics.get_pass_fail_trends(
            days=days,
            playbook_path=playbook_path,
        )

        # Get detailed executions
        if include_executions:
            report.executions = self._get_execution_details(
                playbook_path=playbook_path,
                start_time=start_time,
                end_time=end_time,
                limit=execution_limit,
            )

        logger.info(f"Generated playbook report for {playbook_path}: {report.overall_stats.total_executions} executions")
        return report

    def generate_detailed_report(
        self,
        days: int = 7,
        execution_limit: int = 500,
        status_filter: str | None = None,
    ) -> Report:
        """
        Generate a detailed report with all executions

        Args:
            days: Number of days to include
            execution_limit: Maximum executions to include
            status_filter: Filter by status (passed, failed, etc.)

        Returns:
            Generated Report object
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        report = Report(
            title=f"Detailed Execution Report ({days} days)",
            generated_at=datetime.now(UTC),
            period_start=start_time,
            period_end=end_time,
            metadata={
                "report_type": "detailed",
                "days": days,
                "status_filter": status_filter,
            },
        )

        # Get overall stats
        report.overall_stats = self.analytics.get_overall_stats(
            start_time=start_time,
            end_time=end_time,
        )

        # Get all executions
        report.executions = self._get_execution_details(
            start_time=start_time,
            end_time=end_time,
            limit=execution_limit,
            status_filter=status_filter,
        )

        logger.info(f"Generated detailed report: {len(report.executions)} executions")
        return report

    def _get_execution_details(
        self,
        playbook_path: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        status_filter: str | None = None,
    ) -> list[ExecutionDetail]:
        """
        Get detailed execution information

        Args:
            playbook_path: Filter by playbook
            start_time: Filter after this time
            end_time: Filter before this time
            limit: Maximum results
            status_filter: Filter by status

        Returns:
            List of ExecutionDetail objects
        """
        # Build query conditions
        conditions = []
        params: list[Any] = []

        if playbook_path:
            conditions.append("playbook_path = ?")
            params.append(playbook_path)

        if start_time:
            conditions.append("started_at >= ?")
            params.append(start_time.isoformat())

        if end_time:
            conditions.append("started_at <= ?")
            params.append(end_time.isoformat())

        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                id,
                playbook_path,
                status,
                started_at,
                completed_at,
                error_message,
                parameters
            FROM executions
            {where_clause}
            ORDER BY started_at DESC
            LIMIT ?
        """
        params.append(limit)

        try:
            conn = self.db._get_connection()
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to query execution details: {e}")
            return []

        executions = []
        for row in rows:
            exec_id = row[0]
            path = row[1]
            status = row[2]
            started_at = row[3]
            completed_at = row[4]
            error_message = row[5]
            parameters = row[6]

            # Parse timestamps
            start_dt = None
            end_dt = None
            duration = None

            if started_at:
                try:
                    start_dt = datetime.fromisoformat(started_at)
                except (ValueError, TypeError):
                    pass

            if completed_at:
                try:
                    end_dt = datetime.fromisoformat(completed_at)
                except (ValueError, TypeError):
                    pass

            if start_dt and end_dt:
                duration = (end_dt - start_dt).total_seconds()

            # Parse parameters
            params_dict = {}
            if parameters:
                try:
                    import json
                    params_dict = json.loads(parameters)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Get step counts
            step_query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM execution_steps
                WHERE execution_id = ?
            """

            total_steps = 0
            passed_steps = 0
            failed_steps = 0

            try:
                step_cursor = conn.execute(step_query, [exec_id])
                step_row = step_cursor.fetchone()
                if step_row:
                    total_steps = step_row[0] or 0
                    passed_steps = step_row[1] or 0
                    failed_steps = step_row[2] or 0
            except Exception:
                pass

            playbook_name = path.split("/")[-1] if path else "Unknown"

            executions.append(ExecutionDetail(
                id=exec_id,
                playbook_path=path,
                playbook_name=playbook_name,
                status=status,
                started_at=start_dt,
                completed_at=end_dt,
                duration_seconds=duration,
                total_steps=total_steps,
                passed_steps=passed_steps,
                failed_steps=failed_steps,
                error_message=error_message,
                parameters=params_dict,
            ))

        return executions


# Global instance
_generator: ReportGenerator | None = None


def get_report_generator() -> ReportGenerator:
    """Get the global report generator instance"""
    global _generator
    if _generator is None:
        _generator = ReportGenerator()
    return _generator

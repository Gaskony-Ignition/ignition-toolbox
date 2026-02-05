"""
Execution Analytics

Provides statistical analysis of playbook execution history.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from ignition_toolkit.storage.database import get_database

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStats:
    """Statistics for a set of executions"""
    total_executions: int = 0
    passed: int = 0
    failed: int = 0
    running: int = 0
    cancelled: int = 0
    pass_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    min_duration_seconds: float | None = None
    max_duration_seconds: float | None = None
    total_steps: int = 0
    steps_passed: int = 0
    steps_failed: int = 0


@dataclass
class TrendPoint:
    """Single point in a trend analysis"""
    date: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0


@dataclass
class PlaybookStats:
    """Statistics for a specific playbook"""
    playbook_path: str
    playbook_name: str
    total_executions: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    last_execution: datetime | None = None
    last_status: str | None = None


class ExecutionAnalytics:
    """
    Execution Analytics

    Analyzes playbook execution history to provide:
    - Overall statistics
    - Pass/fail trends over time
    - Per-playbook statistics
    - Performance metrics

    Example:
        analytics = ExecutionAnalytics()

        # Get overall stats
        stats = analytics.get_overall_stats()
        print(f"Pass rate: {stats.pass_rate:.1%}")

        # Get trend data for last 30 days
        trends = analytics.get_pass_fail_trends(days=30)

        # Get per-playbook stats
        playbook_stats = analytics.get_playbook_stats()
    """

    def __init__(self):
        self.db = get_database()

    def get_overall_stats(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        playbook_path: str | None = None,
    ) -> ExecutionStats:
        """
        Get overall execution statistics

        Args:
            start_time: Filter executions after this time
            end_time: Filter executions before this time
            playbook_path: Filter by specific playbook

        Returns:
            ExecutionStats with aggregated statistics
        """
        # Build query conditions
        conditions = []
        params: list[Any] = []

        if start_time:
            conditions.append("started_at >= ?")
            params.append(start_time.isoformat())

        if end_time:
            conditions.append("started_at <= ?")
            params.append(end_time.isoformat())

        if playbook_path:
            conditions.append("playbook_path = ?")
            params.append(playbook_path)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Query executions
        query = f"""
            SELECT
                status,
                started_at,
                completed_at,
                playbook_path
            FROM executions
            {where_clause}
        """

        try:
            conn = self.db._get_connection()
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to query executions: {e}")
            return ExecutionStats()

        if not rows:
            return ExecutionStats()

        # Calculate statistics
        stats = ExecutionStats()
        stats.total_executions = len(rows)

        durations = []
        for row in rows:
            status = row[0]
            started_at = row[1]
            completed_at = row[2]

            if status == "passed":
                stats.passed += 1
            elif status == "failed":
                stats.failed += 1
            elif status == "running":
                stats.running += 1
            elif status == "cancelled":
                stats.cancelled += 1

            # Calculate duration if both timestamps exist
            if started_at and completed_at:
                try:
                    start = datetime.fromisoformat(started_at)
                    end = datetime.fromisoformat(completed_at)
                    duration = (end - start).total_seconds()
                    if duration >= 0:
                        durations.append(duration)
                except (ValueError, TypeError):
                    pass

        # Calculate pass rate
        completed = stats.passed + stats.failed
        if completed > 0:
            stats.pass_rate = stats.passed / completed

        # Calculate duration stats
        if durations:
            stats.avg_duration_seconds = sum(durations) / len(durations)
            stats.min_duration_seconds = min(durations)
            stats.max_duration_seconds = max(durations)

        # Get step statistics
        step_query = f"""
            SELECT
                s.status
            FROM execution_steps s
            JOIN executions e ON s.execution_id = e.id
            {where_clause}
        """

        try:
            cursor = conn.execute(step_query, params)
            step_rows = cursor.fetchall()

            for row in step_rows:
                stats.total_steps += 1
                if row[0] == "passed":
                    stats.steps_passed += 1
                elif row[0] == "failed":
                    stats.steps_failed += 1
        except Exception as e:
            logger.warning(f"Failed to query step statistics: {e}")

        return stats

    def get_pass_fail_trends(
        self,
        days: int = 30,
        playbook_path: str | None = None,
        granularity: str = "day",
    ) -> list[TrendPoint]:
        """
        Get pass/fail trends over time

        Args:
            days: Number of days to analyze
            playbook_path: Filter by specific playbook
            granularity: "day", "week", or "month"

        Returns:
            List of TrendPoint objects
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        # Build query conditions
        conditions = ["started_at >= ?", "started_at <= ?"]
        params: list[Any] = [start_time.isoformat(), end_time.isoformat()]

        if playbook_path:
            conditions.append("playbook_path = ?")
            params.append(playbook_path)

        where_clause = f"WHERE {' AND '.join(conditions)}"

        # Determine date grouping
        if granularity == "week":
            date_expr = "strftime('%Y-W%W', started_at)"
        elif granularity == "month":
            date_expr = "strftime('%Y-%m', started_at)"
        else:  # day
            date_expr = "date(started_at)"

        query = f"""
            SELECT
                {date_expr} as period,
                status,
                COUNT(*) as count
            FROM executions
            {where_clause}
            GROUP BY period, status
            ORDER BY period
        """

        try:
            conn = self.db._get_connection()
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to query trends: {e}")
            return []

        # Aggregate by period
        period_data: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "passed": 0, "failed": 0}
        )

        for row in rows:
            period = row[0]
            status = row[1]
            count = row[2]

            period_data[period]["total"] += count
            if status == "passed":
                period_data[period]["passed"] += count
            elif status == "failed":
                period_data[period]["failed"] += count

        # Convert to TrendPoint list
        trends = []
        for period in sorted(period_data.keys()):
            data = period_data[period]
            completed = data["passed"] + data["failed"]
            pass_rate = data["passed"] / completed if completed > 0 else 0.0

            trends.append(TrendPoint(
                date=period,
                total=data["total"],
                passed=data["passed"],
                failed=data["failed"],
                pass_rate=pass_rate,
            ))

        return trends

    def get_playbook_stats(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
    ) -> list[PlaybookStats]:
        """
        Get statistics for each playbook

        Args:
            start_time: Filter executions after this time
            end_time: Filter executions before this time
            limit: Maximum number of playbooks to return

        Returns:
            List of PlaybookStats sorted by execution count
        """
        # Build query conditions
        conditions = []
        params: list[Any] = []

        if start_time:
            conditions.append("started_at >= ?")
            params.append(start_time.isoformat())

        if end_time:
            conditions.append("started_at <= ?")
            params.append(end_time.isoformat())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                playbook_path,
                status,
                started_at,
                completed_at
            FROM executions
            {where_clause}
            ORDER BY playbook_path, started_at DESC
        """

        try:
            conn = self.db._get_connection()
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to query playbook stats: {e}")
            return []

        # Aggregate by playbook
        playbook_data: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "durations": [],
                "last_execution": None,
                "last_status": None,
            }
        )

        for row in rows:
            playbook_path = row[0]
            status = row[1]
            started_at = row[2]
            completed_at = row[3]

            data = playbook_data[playbook_path]
            data["total"] += 1

            if status == "passed":
                data["passed"] += 1
            elif status == "failed":
                data["failed"] += 1

            # Track last execution
            if data["last_execution"] is None:
                data["last_execution"] = started_at
                data["last_status"] = status

            # Calculate duration
            if started_at and completed_at:
                try:
                    start = datetime.fromisoformat(started_at)
                    end = datetime.fromisoformat(completed_at)
                    duration = (end - start).total_seconds()
                    if duration >= 0:
                        data["durations"].append(duration)
                except (ValueError, TypeError):
                    pass

        # Convert to PlaybookStats list
        stats_list = []
        for playbook_path, data in playbook_data.items():
            completed = data["passed"] + data["failed"]
            pass_rate = data["passed"] / completed if completed > 0 else 0.0
            avg_duration = (
                sum(data["durations"]) / len(data["durations"])
                if data["durations"]
                else 0.0
            )

            # Extract playbook name from path
            playbook_name = playbook_path.split("/")[-1] if playbook_path else "Unknown"

            last_exec = None
            if data["last_execution"]:
                try:
                    last_exec = datetime.fromisoformat(data["last_execution"])
                except (ValueError, TypeError):
                    pass

            stats_list.append(PlaybookStats(
                playbook_path=playbook_path,
                playbook_name=playbook_name,
                total_executions=data["total"],
                passed=data["passed"],
                failed=data["failed"],
                pass_rate=pass_rate,
                avg_duration_seconds=avg_duration,
                last_execution=last_exec,
                last_status=data["last_status"],
            ))

        # Sort by execution count and limit
        stats_list.sort(key=lambda x: x.total_executions, reverse=True)
        return stats_list[:limit]

    def get_failure_analysis(
        self,
        days: int = 30,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Analyze common failure patterns

        Args:
            days: Number of days to analyze
            limit: Maximum number of failure patterns to return

        Returns:
            List of failure patterns with counts
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        query = """
            SELECT
                s.step_id,
                s.step_type,
                s.error_message,
                e.playbook_path,
                COUNT(*) as count
            FROM execution_steps s
            JOIN executions e ON s.execution_id = e.id
            WHERE s.status = 'failed'
                AND e.started_at >= ?
                AND e.started_at <= ?
                AND s.error_message IS NOT NULL
            GROUP BY s.step_type, s.error_message
            ORDER BY count DESC
            LIMIT ?
        """

        try:
            conn = self.db._get_connection()
            cursor = conn.execute(
                query,
                [start_time.isoformat(), end_time.isoformat(), limit]
            )
            rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to query failure analysis: {e}")
            return []

        failures = []
        for row in rows:
            failures.append({
                "step_id": row[0],
                "step_type": row[1],
                "error_message": row[2],
                "playbook_path": row[3],
                "count": row[4],
            })

        return failures


# Global instance
_analytics: ExecutionAnalytics | None = None


def get_execution_analytics() -> ExecutionAnalytics:
    """Get the global execution analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = ExecutionAnalytics()
    return _analytics

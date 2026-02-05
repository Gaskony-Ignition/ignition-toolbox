"""
Reporting API Router

Provides endpoints for:
- Execution statistics
- Pass/fail trends
- Report generation
- Export to CSV/JSON
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ignition_toolkit.reporting.analytics import get_execution_analytics
from ignition_toolkit.reporting.reports import get_report_generator
from ignition_toolkit.reporting.export import get_report_exporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reporting"])


# Request/Response Models

class GenerateReportRequest(BaseModel):
    """Request to generate a report"""
    report_type: str = Field(default="summary", description="Report type: summary, playbook, detailed")
    days: int = Field(default=30, ge=1, le=365, description="Number of days to include")
    playbook_path: str | None = Field(default=None, description="Playbook path (for playbook report)")
    include_trends: bool = Field(default=True)
    include_playbook_stats: bool = Field(default=True)
    include_failure_analysis: bool = Field(default=True)
    include_executions: bool = Field(default=True)
    trend_granularity: str = Field(default="day", description="Trend granularity: day, week, month")
    execution_limit: int = Field(default=100, ge=1, le=1000)
    status_filter: str | None = Field(default=None, description="Filter by status")


# Statistics Endpoints

@router.get("/stats")
async def get_overall_stats(
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    playbook_path: str | None = Query(default=None, description="Filter by playbook"),
):
    """
    Get overall execution statistics

    Returns aggregated statistics for the specified time period.
    """
    analytics = get_execution_analytics()

    from datetime import UTC, timedelta
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)

    stats = analytics.get_overall_stats(
        start_time=start_time,
        end_time=end_time,
        playbook_path=playbook_path,
    )

    return {
        "period_days": days,
        "playbook_filter": playbook_path,
        "stats": {
            "total_executions": stats.total_executions,
            "passed": stats.passed,
            "failed": stats.failed,
            "running": stats.running,
            "cancelled": stats.cancelled,
            "pass_rate": stats.pass_rate,
            "avg_duration_seconds": stats.avg_duration_seconds,
            "min_duration_seconds": stats.min_duration_seconds,
            "max_duration_seconds": stats.max_duration_seconds,
            "total_steps": stats.total_steps,
            "steps_passed": stats.steps_passed,
            "steps_failed": stats.steps_failed,
        },
    }


@router.get("/trends")
async def get_trends(
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    playbook_path: str | None = Query(default=None, description="Filter by playbook"),
    granularity: str = Query(default="day", description="Granularity: day, week, month"),
):
    """
    Get pass/fail trends over time

    Returns daily/weekly/monthly trend data for charting.
    """
    if granularity not in ["day", "week", "month"]:
        raise HTTPException(status_code=400, detail="Invalid granularity. Use: day, week, month")

    analytics = get_execution_analytics()

    trends = analytics.get_pass_fail_trends(
        days=days,
        playbook_path=playbook_path,
        granularity=granularity,
    )

    return {
        "period_days": days,
        "playbook_filter": playbook_path,
        "granularity": granularity,
        "trends": [
            {
                "date": t.date,
                "total": t.total,
                "passed": t.passed,
                "failed": t.failed,
                "pass_rate": t.pass_rate,
            }
            for t in trends
        ],
    }


@router.get("/playbooks")
async def get_playbook_stats(
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum playbooks to return"),
):
    """
    Get statistics per playbook

    Returns statistics for each playbook, sorted by execution count.
    """
    analytics = get_execution_analytics()

    from datetime import UTC, timedelta
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)

    stats = analytics.get_playbook_stats(
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    return {
        "period_days": days,
        "count": len(stats),
        "playbooks": [
            {
                "playbook_path": s.playbook_path,
                "playbook_name": s.playbook_name,
                "total_executions": s.total_executions,
                "passed": s.passed,
                "failed": s.failed,
                "pass_rate": s.pass_rate,
                "avg_duration_seconds": s.avg_duration_seconds,
                "last_execution": s.last_execution.isoformat() if s.last_execution else None,
                "last_status": s.last_status,
            }
            for s in stats
        ],
    }


@router.get("/failures")
async def get_failure_analysis(
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum failures to return"),
):
    """
    Get failure pattern analysis

    Returns common failure patterns to help identify recurring issues.
    """
    analytics = get_execution_analytics()

    failures = analytics.get_failure_analysis(days=days, limit=limit)

    return {
        "period_days": days,
        "count": len(failures),
        "failures": failures,
    }


# Report Generation Endpoints

@router.post("/generate")
async def generate_report(request: GenerateReportRequest):
    """
    Generate a report

    Creates a comprehensive report based on the specified parameters.
    """
    generator = get_report_generator()

    try:
        if request.report_type == "summary":
            report = generator.generate_summary_report(
                days=request.days,
                include_trends=request.include_trends,
                include_playbook_stats=request.include_playbook_stats,
                include_failure_analysis=request.include_failure_analysis,
                trend_granularity=request.trend_granularity,
            )
        elif request.report_type == "playbook":
            if not request.playbook_path:
                raise HTTPException(
                    status_code=400,
                    detail="playbook_path is required for playbook report"
                )
            report = generator.generate_playbook_report(
                playbook_path=request.playbook_path,
                days=request.days,
                include_executions=request.include_executions,
                execution_limit=request.execution_limit,
            )
        elif request.report_type == "detailed":
            report = generator.generate_detailed_report(
                days=request.days,
                execution_limit=request.execution_limit,
                status_filter=request.status_filter,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report_type: {request.report_type}. Use: summary, playbook, detailed"
            )

        return report.to_dict()

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary_report(
    days: int = Query(default=30, ge=1, le=365),
    trend_granularity: str = Query(default="day"),
):
    """
    Get a summary report (convenience endpoint)

    Shortcut for generating a summary report with default options.
    """
    generator = get_report_generator()

    try:
        report = generator.generate_summary_report(
            days=days,
            trend_granularity=trend_granularity,
        )
        return report.to_dict()
    except Exception as e:
        logger.error(f"Failed to generate summary report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export Endpoints

@router.post("/export/json")
async def export_report_json(request: GenerateReportRequest):
    """
    Export report as JSON

    Generates a report and returns it as a downloadable JSON file.
    """
    generator = get_report_generator()
    exporter = get_report_exporter()

    try:
        # Generate report based on type
        if request.report_type == "summary":
            report = generator.generate_summary_report(
                days=request.days,
                include_trends=request.include_trends,
                include_playbook_stats=request.include_playbook_stats,
                include_failure_analysis=request.include_failure_analysis,
                trend_granularity=request.trend_granularity,
            )
        elif request.report_type == "playbook":
            if not request.playbook_path:
                raise HTTPException(status_code=400, detail="playbook_path required")
            report = generator.generate_playbook_report(
                playbook_path=request.playbook_path,
                days=request.days,
                include_executions=request.include_executions,
                execution_limit=request.execution_limit,
            )
        else:
            report = generator.generate_detailed_report(
                days=request.days,
                execution_limit=request.execution_limit,
                status_filter=request.status_filter,
            )

        json_content = exporter.to_json(report)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{request.report_type}_{timestamp}.json"

        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    except Exception as e:
        logger.error(f"Failed to export JSON report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/csv")
async def export_report_csv(request: GenerateReportRequest):
    """
    Export report as CSV

    Generates a report and returns it as a downloadable CSV file.
    """
    generator = get_report_generator()
    exporter = get_report_exporter()

    try:
        # Generate report based on type
        if request.report_type == "summary":
            report = generator.generate_summary_report(
                days=request.days,
                include_trends=request.include_trends,
                include_playbook_stats=request.include_playbook_stats,
                include_failure_analysis=request.include_failure_analysis,
                trend_granularity=request.trend_granularity,
            )
        elif request.report_type == "playbook":
            if not request.playbook_path:
                raise HTTPException(status_code=400, detail="playbook_path required")
            report = generator.generate_playbook_report(
                playbook_path=request.playbook_path,
                days=request.days,
                include_executions=request.include_executions,
                execution_limit=request.execution_limit,
            )
        else:
            report = generator.generate_detailed_report(
                days=request.days,
                execution_limit=request.execution_limit,
                status_filter=request.status_filter,
            )

        csv_content = exporter.to_csv(
            report,
            include_summary=True,
            include_executions=request.include_executions,
            include_playbook_stats=request.include_playbook_stats,
        )

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{request.report_type}_{timestamp}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    except Exception as e:
        logger.error(f"Failed to export CSV report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/executions/csv")
async def export_executions_csv(
    days: int = Query(default=7, ge=1, le=365),
    limit: int = Query(default=500, ge=1, le=5000),
    status: str | None = Query(default=None),
):
    """
    Export executions as CSV (simple format)

    Returns a simple CSV with execution data only, suitable for spreadsheet analysis.
    """
    generator = get_report_generator()
    exporter = get_report_exporter()

    try:
        report = generator.generate_detailed_report(
            days=days,
            execution_limit=limit,
            status_filter=status,
        )

        csv_content = exporter.to_executions_csv(report)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"executions_{timestamp}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    except Exception as e:
        logger.error(f"Failed to export executions CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

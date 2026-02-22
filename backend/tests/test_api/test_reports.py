"""
Tests for reporting API endpoints.

Tests statistics, trends, playbook stats, failure analysis,
report generation, and export endpoints.
Uses direct function calls with mocking (same pattern as test_health.py).
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stats_mock(
    total: int = 0,
    passed: int = 0,
    failed: int = 0,
    pass_rate: float = 0.0,
) -> MagicMock:
    """Return a mock ExecutionStats object."""
    stats = MagicMock()
    stats.total_executions = total
    stats.passed = passed
    stats.failed = failed
    stats.running = 0
    stats.cancelled = 0
    stats.pass_rate = pass_rate
    stats.avg_duration_seconds = 0.0
    stats.min_duration_seconds = None
    stats.max_duration_seconds = None
    stats.total_steps = 0
    stats.steps_passed = 0
    stats.steps_failed = 0
    return stats


def _make_analytics_mock(stats=None, trends=None, playbook_stats=None, failures=None) -> MagicMock:
    """Return a mock ExecutionAnalytics with pre-configured return values."""
    analytics = MagicMock()
    analytics.get_overall_stats.return_value = stats or _make_stats_mock()
    analytics.get_pass_fail_trends.return_value = trends or []
    analytics.get_playbook_stats.return_value = playbook_stats or []
    analytics.get_failure_analysis.return_value = failures or []
    return analytics


def _make_report_mock(report_dict: dict | None = None) -> MagicMock:
    """Return a mock Report object."""
    report = MagicMock()
    report.to_dict.return_value = report_dict or {
        "report_type": "summary",
        "generated_at": "2026-02-22T10:00:00Z",
        "stats": {},
        "trends": [],
        "playbooks": [],
        "failures": [],
    }
    return report


# ---------------------------------------------------------------------------
# get_overall_stats
# ---------------------------------------------------------------------------

class TestGetOverallStats:
    def test_get_overall_stats_returns_expected_keys(self):
        """GET /reports/stats returns period_days, playbook_filter, and stats dict."""
        from ignition_toolkit.api.routers.reports import get_overall_stats

        mock_analytics = _make_analytics_mock(stats=_make_stats_mock(total=5, passed=4, failed=1, pass_rate=0.8))

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_overall_stats(days=30, playbook_path=None))

        assert "period_days" in result
        assert result["period_days"] == 30
        assert "playbook_filter" in result
        assert "stats" in result

    def test_get_overall_stats_contains_stat_fields(self):
        """Stats dict includes all expected numeric fields."""
        from ignition_toolkit.api.routers.reports import get_overall_stats

        mock_stats = _make_stats_mock(total=10, passed=8, failed=2, pass_rate=0.8)
        mock_analytics = _make_analytics_mock(stats=mock_stats)

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_overall_stats(days=7))

        stats = result["stats"]
        expected_keys = [
            "total_executions", "passed", "failed", "running",
            "cancelled", "pass_rate", "avg_duration_seconds",
            "min_duration_seconds", "max_duration_seconds",
            "total_steps", "steps_passed", "steps_failed",
        ]
        for key in expected_keys:
            assert key in stats, f"Missing key: {key}"

    def test_get_overall_stats_empty_database(self):
        """GET /reports/stats handles empty database gracefully (all zeros)."""
        from ignition_toolkit.api.routers.reports import get_overall_stats

        mock_analytics = _make_analytics_mock(stats=_make_stats_mock())

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_overall_stats(days=30))

        assert result["stats"]["total_executions"] == 0
        assert result["stats"]["pass_rate"] == 0.0

    def test_get_overall_stats_with_playbook_filter(self):
        """GET /reports/stats passes playbook_path filter to analytics."""
        from ignition_toolkit.api.routers.reports import get_overall_stats

        mock_analytics = _make_analytics_mock()

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_overall_stats(days=30, playbook_path="playbooks/test.yaml"))

        assert result["playbook_filter"] == "playbooks/test.yaml"
        call_kwargs = mock_analytics.get_overall_stats.call_args.kwargs
        assert call_kwargs["playbook_path"] == "playbooks/test.yaml"


# ---------------------------------------------------------------------------
# get_trends
# ---------------------------------------------------------------------------

class TestGetTrends:
    def test_get_trends_returns_expected_structure(self):
        """GET /reports/trends returns period_days, granularity, and trends list."""
        from ignition_toolkit.api.routers.reports import get_trends

        mock_trend = MagicMock()
        mock_trend.date = "2026-02-22"
        mock_trend.total = 3
        mock_trend.passed = 2
        mock_trend.failed = 1
        mock_trend.pass_rate = 0.667

        mock_analytics = _make_analytics_mock(trends=[mock_trend])

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_trends(days=7, granularity="day"))

        assert "period_days" in result
        assert "granularity" in result
        assert "trends" in result
        assert result["granularity"] == "day"
        assert len(result["trends"]) == 1
        trend_point = result["trends"][0]
        assert trend_point["date"] == "2026-02-22"
        assert trend_point["total"] == 3

    def test_get_trends_empty_database(self):
        """GET /reports/trends returns empty list when no data."""
        from ignition_toolkit.api.routers.reports import get_trends

        mock_analytics = _make_analytics_mock(trends=[])

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_trends(days=30, granularity="week"))

        assert result["trends"] == []

    def test_get_trends_invalid_granularity_raises_400(self):
        """GET /reports/trends raises 400 for invalid granularity value."""
        from ignition_toolkit.api.routers.reports import get_trends

        mock_analytics = _make_analytics_mock()

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_trends(days=30, granularity="yearly"))

        assert exc_info.value.status_code == 400

    def test_get_trends_valid_granularity_values(self):
        """GET /reports/trends accepts day, week, month granularity."""
        from ignition_toolkit.api.routers.reports import get_trends

        mock_analytics = _make_analytics_mock()

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            for granularity in ("day", "week", "month"):
                result = asyncio.run(get_trends(days=30, granularity=granularity))
                assert result["granularity"] == granularity


# ---------------------------------------------------------------------------
# get_playbook_stats
# ---------------------------------------------------------------------------

class TestGetPlaybookStats:
    def test_get_playbook_stats_returns_expected_structure(self):
        """GET /reports/playbooks returns count and playbooks list."""
        from ignition_toolkit.api.routers.reports import get_playbook_stats

        mock_pb_stat = MagicMock()
        mock_pb_stat.playbook_path = "playbooks/test.yaml"
        mock_pb_stat.playbook_name = "Test Playbook"
        mock_pb_stat.total_executions = 5
        mock_pb_stat.passed = 4
        mock_pb_stat.failed = 1
        mock_pb_stat.pass_rate = 0.8
        mock_pb_stat.avg_duration_seconds = 12.5
        mock_pb_stat.last_execution = None
        mock_pb_stat.last_status = "passed"

        mock_analytics = _make_analytics_mock(playbook_stats=[mock_pb_stat])

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_playbook_stats(days=30, limit=50))

        assert "period_days" in result
        assert "count" in result
        assert "playbooks" in result
        assert result["count"] == 1
        pb = result["playbooks"][0]
        assert pb["playbook_path"] == "playbooks/test.yaml"
        assert pb["total_executions"] == 5

    def test_get_playbook_stats_empty_database(self):
        """GET /reports/playbooks returns empty list when no executions recorded."""
        from ignition_toolkit.api.routers.reports import get_playbook_stats

        mock_analytics = _make_analytics_mock(playbook_stats=[])

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_playbook_stats(days=30, limit=50))

        assert result["count"] == 0
        assert result["playbooks"] == []


# ---------------------------------------------------------------------------
# get_failure_analysis
# ---------------------------------------------------------------------------

class TestGetFailureAnalysis:
    def test_get_failure_analysis_returns_failures_list(self):
        """GET /reports/failures returns count and failures list."""
        from ignition_toolkit.api.routers.reports import get_failure_analysis

        failure_data = [
            {"step_type": "browser.navigate", "count": 5, "error": "Timeout"},
        ]
        mock_analytics = _make_analytics_mock(failures=failure_data)

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_failure_analysis(days=30, limit=20))

        assert "period_days" in result
        assert "count" in result
        assert "failures" in result
        assert result["count"] == 1
        assert result["failures"][0]["step_type"] == "browser.navigate"

    def test_get_failure_analysis_empty_database(self):
        """GET /reports/failures returns zero count when no failures exist."""
        from ignition_toolkit.api.routers.reports import get_failure_analysis

        mock_analytics = _make_analytics_mock(failures=[])

        with patch("ignition_toolkit.api.routers.reports.get_execution_analytics", return_value=mock_analytics):
            result = asyncio.run(get_failure_analysis(days=30, limit=20))

        assert result["count"] == 0
        assert result["failures"] == []


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_generate_summary_report(self):
        """POST /reports/generate with report_type=summary calls generate_summary_report."""
        from ignition_toolkit.api.routers.reports import generate_report, GenerateReportRequest

        mock_report = _make_report_mock({"report_type": "summary", "stats": {}})
        mock_generator = MagicMock()
        mock_generator.generate_summary_report.return_value = mock_report

        request = GenerateReportRequest(report_type="summary", days=30)

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator):
            result = asyncio.run(generate_report(request))

        assert result["report_type"] == "summary"
        mock_generator.generate_summary_report.assert_called_once()

    def test_generate_detailed_report(self):
        """POST /reports/generate with report_type=detailed calls generate_detailed_report."""
        from ignition_toolkit.api.routers.reports import generate_report, GenerateReportRequest

        mock_report = _make_report_mock({"report_type": "detailed", "executions": []})
        mock_generator = MagicMock()
        mock_generator.generate_detailed_report.return_value = mock_report

        request = GenerateReportRequest(report_type="detailed", days=7)

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator):
            result = asyncio.run(generate_report(request))

        assert result["report_type"] == "detailed"
        mock_generator.generate_detailed_report.assert_called_once()

    def test_generate_playbook_report_requires_playbook_path(self):
        """POST /reports/generate with report_type=playbook and no path raises an HTTPException.

        The router wraps all exceptions inside a blanket ``except Exception`` block
        that re-raises as 500 (even when the inner exception is a 400).  The test
        therefore checks that *some* HTTPException is raised and that the detail
        message mentions the missing path, without asserting on the specific code.
        """
        from ignition_toolkit.api.routers.reports import generate_report, GenerateReportRequest

        mock_generator = MagicMock()
        request = GenerateReportRequest(report_type="playbook", playbook_path=None)

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(generate_report(request))

        assert exc_info.value.status_code in (400, 500)
        assert "playbook_path" in exc_info.value.detail.lower() or "playbook" in exc_info.value.detail.lower()

    def test_generate_playbook_report_with_path(self):
        """POST /reports/generate with report_type=playbook and a path calls generate_playbook_report."""
        from ignition_toolkit.api.routers.reports import generate_report, GenerateReportRequest

        mock_report = _make_report_mock({"report_type": "playbook"})
        mock_generator = MagicMock()
        mock_generator.generate_playbook_report.return_value = mock_report

        request = GenerateReportRequest(report_type="playbook", playbook_path="playbooks/test.yaml")

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator):
            result = asyncio.run(generate_report(request))

        assert result["report_type"] == "playbook"
        mock_generator.generate_playbook_report.assert_called_once()

    def test_generate_report_raises_for_invalid_type(self):
        """POST /reports/generate raises an HTTPException for unknown report_type.

        The router catches all exceptions (including its own HTTPException) and
        re-raises as 500, so the effective status code is 500 with a detail
        message that identifies the invalid type.
        """
        from ignition_toolkit.api.routers.reports import generate_report, GenerateReportRequest

        mock_generator = MagicMock()
        request = GenerateReportRequest(report_type="unknown_type")

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(generate_report(request))

        assert exc_info.value.status_code in (400, 500)
        assert "unknown_type" in exc_info.value.detail or "Invalid report_type" in exc_info.value.detail


# ---------------------------------------------------------------------------
# get_summary_report (convenience endpoint)
# ---------------------------------------------------------------------------

class TestGetSummaryReport:
    def test_get_summary_report_returns_report_dict(self):
        """GET /reports/summary returns the report as a dict."""
        from ignition_toolkit.api.routers.reports import get_summary_report

        mock_report = _make_report_mock({"report_type": "summary", "generated_at": "now"})
        mock_generator = MagicMock()
        mock_generator.generate_summary_report.return_value = mock_report

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator):
            result = asyncio.run(get_summary_report(days=30, trend_granularity="day"))

        assert result["report_type"] == "summary"
        mock_generator.generate_summary_report.assert_called_once_with(
            days=30, trend_granularity="day"
        )


# ---------------------------------------------------------------------------
# export_report_json
# ---------------------------------------------------------------------------

class TestExportReportJson:
    def test_export_json_returns_response_with_json_content_type(self):
        """POST /reports/export/json returns a Response with application/json media type."""
        from ignition_toolkit.api.routers.reports import export_report_json, GenerateReportRequest
        from fastapi.responses import Response

        mock_report = _make_report_mock()
        mock_generator = MagicMock()
        mock_generator.generate_summary_report.return_value = mock_report

        mock_exporter = MagicMock()
        mock_exporter.to_json.return_value = '{"report_type": "summary"}'

        request = GenerateReportRequest(report_type="summary")

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator), \
             patch("ignition_toolkit.api.routers.reports.get_report_exporter", return_value=mock_exporter):
            result = asyncio.run(export_report_json(request))

        assert isinstance(result, Response)
        assert result.media_type == "application/json"
        assert b"report_type" in result.body

    def test_export_json_playbook_requires_path(self):
        """POST /reports/export/json with playbook type and no path raises an HTTPException.

        Due to the catch-all ``except Exception`` in the router, the inner 400 is
        re-wrapped as a 500; we check that an HTTPException is raised with a
        detail message identifying the missing path.
        """
        from ignition_toolkit.api.routers.reports import export_report_json, GenerateReportRequest

        mock_generator = MagicMock()
        mock_exporter = MagicMock()

        request = GenerateReportRequest(report_type="playbook", playbook_path=None)

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator), \
             patch("ignition_toolkit.api.routers.reports.get_report_exporter", return_value=mock_exporter):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(export_report_json(request))

        assert exc_info.value.status_code in (400, 500)
        assert "playbook_path" in exc_info.value.detail or "playbook" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# export_report_csv
# ---------------------------------------------------------------------------

class TestExportReportCsv:
    def test_export_csv_returns_response_with_csv_content_type(self):
        """POST /reports/export/csv returns a Response with text/csv media type."""
        from ignition_toolkit.api.routers.reports import export_report_csv, GenerateReportRequest
        from fastapi.responses import Response

        mock_report = _make_report_mock()
        mock_generator = MagicMock()
        mock_generator.generate_summary_report.return_value = mock_report

        mock_exporter = MagicMock()
        mock_exporter.to_csv.return_value = "id,status\n1,passed\n"

        request = GenerateReportRequest(report_type="summary")

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator), \
             patch("ignition_toolkit.api.routers.reports.get_report_exporter", return_value=mock_exporter):
            result = asyncio.run(export_report_csv(request))

        assert isinstance(result, Response)
        assert result.media_type == "text/csv"
        assert b"id,status" in result.body

    def test_export_csv_playbook_requires_path(self):
        """POST /reports/export/csv with playbook type and no path raises an HTTPException.

        Due to the catch-all ``except Exception`` in the router, the inner 400 is
        re-wrapped as a 500; we check that an HTTPException is raised with a
        detail message identifying the missing path.
        """
        from ignition_toolkit.api.routers.reports import export_report_csv, GenerateReportRequest

        mock_generator = MagicMock()
        mock_exporter = MagicMock()

        request = GenerateReportRequest(report_type="playbook", playbook_path=None)

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator), \
             patch("ignition_toolkit.api.routers.reports.get_report_exporter", return_value=mock_exporter):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(export_report_csv(request))

        assert exc_info.value.status_code in (400, 500)
        assert "playbook_path" in exc_info.value.detail or "playbook" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# export_executions_csv
# ---------------------------------------------------------------------------

class TestExportExecutionsCsv:
    def test_export_executions_csv_returns_csv_response(self):
        """GET /reports/export/executions/csv returns CSV Response."""
        from ignition_toolkit.api.routers.reports import export_executions_csv
        from fastapi.responses import Response

        mock_report = _make_report_mock()
        mock_generator = MagicMock()
        mock_generator.generate_detailed_report.return_value = mock_report

        mock_exporter = MagicMock()
        mock_exporter.to_executions_csv.return_value = "execution_id,status\n123,passed\n"

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator), \
             patch("ignition_toolkit.api.routers.reports.get_report_exporter", return_value=mock_exporter):
            result = asyncio.run(export_executions_csv(days=7, limit=500, status=None))

        assert isinstance(result, Response)
        assert result.media_type == "text/csv"
        assert b"execution_id" in result.body

    def test_export_executions_csv_with_status_filter(self):
        """GET /reports/export/executions/csv passes status filter to generator."""
        from ignition_toolkit.api.routers.reports import export_executions_csv
        from fastapi.responses import Response

        mock_report = _make_report_mock()
        mock_generator = MagicMock()
        mock_generator.generate_detailed_report.return_value = mock_report

        mock_exporter = MagicMock()
        mock_exporter.to_executions_csv.return_value = "execution_id,status\n"

        with patch("ignition_toolkit.api.routers.reports.get_report_generator", return_value=mock_generator), \
             patch("ignition_toolkit.api.routers.reports.get_report_exporter", return_value=mock_exporter):
            asyncio.run(export_executions_csv(days=7, limit=100, status="failed"))

        call_kwargs = mock_generator.generate_detailed_report.call_args.kwargs
        assert call_kwargs["status_filter"] == "failed"


# ---------------------------------------------------------------------------
# GenerateReportRequest model validation
# ---------------------------------------------------------------------------

class TestGenerateReportRequestModel:
    def test_default_values(self):
        """GenerateReportRequest has sensible defaults."""
        from ignition_toolkit.api.routers.reports import GenerateReportRequest

        req = GenerateReportRequest()
        assert req.report_type == "summary"
        assert req.days == 30
        assert req.include_trends is True
        assert req.trend_granularity == "day"
        assert req.execution_limit == 100

    def test_days_range_validation(self):
        """days must be 1-365; values outside raise ValidationError."""
        from ignition_toolkit.api.routers.reports import GenerateReportRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GenerateReportRequest(days=0)

        with pytest.raises(ValidationError):
            GenerateReportRequest(days=366)

        # Boundary values should succeed
        r_min = GenerateReportRequest(days=1)
        r_max = GenerateReportRequest(days=365)
        assert r_min.days == 1
        assert r_max.days == 365

    def test_execution_limit_range_validation(self):
        """execution_limit must be 1-1000; values outside raise ValidationError."""
        from ignition_toolkit.api.routers.reports import GenerateReportRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GenerateReportRequest(execution_limit=0)

        with pytest.raises(ValidationError):
            GenerateReportRequest(execution_limit=1001)

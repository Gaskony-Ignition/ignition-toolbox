"""
Tests for logs API endpoints.

Tests get_logs, get_log_stats, get_execution_logs, and clear_logs endpoints.
The log capture service is mocked so no actual logging infrastructure is needed.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_log_entry(
    *,
    level: str = "INFO",
    logger: str = "ignition_toolkit.test",
    message: str = "test message",
    execution_id: str | None = None,
):
    """Return a dict matching the LogEntry dataclass structure."""
    return {
        "timestamp": "2026-01-01T00:00:00.000000",
        "level": level,
        "logger": logger,
        "message": message,
        "execution_id": execution_id,
    }


def _make_capture(entries: list[dict] | None = None, total: int | None = None):
    """Return a MagicMock LogCaptureHandler populated with the given entries."""
    capture = MagicMock()
    entries = entries or []
    capture.get_logs.return_value = entries
    capture.get_stats.return_value = {
        "total_captured": total if total is not None else len(entries),
        "max_entries": 2000,
        "level_counts": {e["level"]: 1 for e in entries},
        "oldest_entry": entries[0]["timestamp"] if entries else None,
        "newest_entry": entries[-1]["timestamp"] if entries else None,
    }
    return capture


# ---------------------------------------------------------------------------
# get_logs
# ---------------------------------------------------------------------------


class TestGetLogs:
    def test_get_logs_returns_empty_when_no_capture(self):
        """When log capture is not set up, get_logs returns empty response."""
        from ignition_toolkit.api.routers.logs import get_logs

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=None,
        ):
            result = asyncio.run(get_logs())

        assert result.logs == []
        assert result.total == 0
        assert result.filtered == 0

    def test_get_logs_returns_all_entries(self):
        """get_logs returns all captured log entries."""
        from ignition_toolkit.api.routers.logs import get_logs

        entries = [
            _make_log_entry(message="first"),
            _make_log_entry(message="second"),
        ]
        capture = _make_capture(entries=entries)

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            result = asyncio.run(get_logs())

        assert result.total == 2
        assert result.filtered == 2
        assert len(result.logs) == 2

    def test_get_logs_filter_by_level(self):
        """Passing level= filters results through the capture service."""
        from ignition_toolkit.api.routers.logs import get_logs

        entries = [_make_log_entry(level="ERROR", message="error message")]
        capture = _make_capture(entries=entries)

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            result = asyncio.run(get_logs(level="ERROR"))

        capture.get_logs.assert_called_once()
        call_kwargs = capture.get_logs.call_args.kwargs
        assert call_kwargs["level"] == "ERROR"

    def test_get_logs_filter_by_logger(self):
        """Passing logger_filter= is forwarded to the capture service."""
        from ignition_toolkit.api.routers.logs import get_logs

        entries = [_make_log_entry(logger="ignition_toolkit.browser")]
        capture = _make_capture(entries=entries)

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            result = asyncio.run(get_logs(logger_filter="browser"))

        call_kwargs = capture.get_logs.call_args.kwargs
        assert call_kwargs["logger_filter"] == "browser"

    def test_get_logs_filter_by_execution_id(self):
        """Passing execution_id= is forwarded to the capture service."""
        from ignition_toolkit.api.routers.logs import get_logs

        exec_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        entries = [_make_log_entry(execution_id=exec_id)]
        capture = _make_capture(entries=entries)

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            result = asyncio.run(get_logs(execution_id=exec_id))

        call_kwargs = capture.get_logs.call_args.kwargs
        assert call_kwargs["execution_id"] == exec_id

    def test_get_logs_respects_limit(self):
        """Passing limit= is forwarded to the capture service."""
        from ignition_toolkit.api.routers.logs import get_logs

        capture = _make_capture(entries=[])

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            asyncio.run(get_logs(limit=42))

        call_kwargs = capture.get_logs.call_args.kwargs
        assert call_kwargs["limit"] == 42

    def test_get_logs_response_total_comes_from_stats(self):
        """The total field in the response comes from get_stats(), not len(logs)."""
        from ignition_toolkit.api.routers.logs import get_logs

        # 1 visible entry, but 500 total captured
        entries = [_make_log_entry()]
        capture = _make_capture(entries=entries, total=500)

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            result = asyncio.run(get_logs())

        assert result.total == 500
        assert result.filtered == 1


# ---------------------------------------------------------------------------
# get_log_stats
# ---------------------------------------------------------------------------


class TestGetLogStats:
    def test_stats_returns_zeros_when_no_capture(self):
        """When log capture is not set up, stats returns zeros."""
        from ignition_toolkit.api.routers.logs import get_log_stats

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=None,
        ):
            result = asyncio.run(get_log_stats())

        assert result.total_captured == 0
        assert result.max_entries == 0
        assert result.level_counts == {}
        assert result.oldest_entry is None
        assert result.newest_entry is None

    def test_stats_returns_capture_statistics(self):
        """get_log_stats returns the stats from the capture handler."""
        from ignition_toolkit.api.routers.logs import get_log_stats

        entries = [
            _make_log_entry(level="INFO"),
            _make_log_entry(level="ERROR"),
        ]
        capture = _make_capture(entries=entries)

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            result = asyncio.run(get_log_stats())

        assert result.total_captured == 2
        assert result.max_entries == 2000
        assert "INFO" in result.level_counts
        assert "ERROR" in result.level_counts


# ---------------------------------------------------------------------------
# get_execution_logs
# ---------------------------------------------------------------------------


class TestGetExecutionLogs:
    def test_execution_logs_returns_empty_when_no_capture(self):
        """When log capture is not set up, execution logs returns empty."""
        from ignition_toolkit.api.routers.logs import get_execution_logs

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=None,
        ):
            result = asyncio.run(get_execution_logs("some-exec-id"))

        assert result.logs == []
        assert result.total == 0

    def test_execution_logs_passes_execution_id_to_capture(self):
        """get_execution_logs forwards the execution_id filter to the capture service."""
        from ignition_toolkit.api.routers.logs import get_execution_logs

        exec_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        entries = [_make_log_entry(execution_id=exec_id)]
        capture = _make_capture(entries=entries)

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            result = asyncio.run(get_execution_logs(exec_id))

        capture.get_logs.assert_called_once()
        call_kwargs = capture.get_logs.call_args.kwargs
        assert call_kwargs["execution_id"] == exec_id
        assert result.filtered == 1

    def test_execution_logs_respects_limit(self):
        """get_execution_logs forwards the limit parameter."""
        from ignition_toolkit.api.routers.logs import get_execution_logs

        capture = _make_capture(entries=[])

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            asyncio.run(get_execution_logs("exec-id", limit=250))

        call_kwargs = capture.get_logs.call_args.kwargs
        assert call_kwargs["limit"] == 250


# ---------------------------------------------------------------------------
# clear_logs
# ---------------------------------------------------------------------------


class TestClearLogs:
    def test_clear_logs_calls_capture_clear(self):
        """clear_logs calls clear() on the capture service and returns success."""
        from ignition_toolkit.api.routers.logs import clear_logs

        capture = MagicMock()

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=capture,
        ):
            result = asyncio.run(clear_logs())

        capture.clear.assert_called_once()
        assert result["success"] is True

    def test_clear_logs_no_capture_returns_success(self):
        """clear_logs returns success even when no capture handler is configured."""
        from ignition_toolkit.api.routers.logs import clear_logs

        with patch(
            "ignition_toolkit.api.routers.logs.get_log_capture",
            return_value=None,
        ):
            result = asyncio.run(clear_logs())

        assert result["success"] is True
        assert "cleared" in result["message"].lower()

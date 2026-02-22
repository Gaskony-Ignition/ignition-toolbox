"""
Log Capture Service

Captures backend logs in memory for UI access.
Provides a circular buffer of recent log entries.
"""

import logging
import threading
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class LogEntry:
    """A single log entry"""
    timestamp: str
    level: str
    logger: str
    message: str
    execution_id: str | None = None


class LogCaptureHandler(logging.Handler):
    """
    Custom logging handler that captures logs to a circular buffer.
    Thread-safe for concurrent access.
    """

    def __init__(self, max_entries: int = 1000):
        super().__init__()
        self.max_entries = max_entries
        self.logs: deque[LogEntry] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

        # Set format
        self.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

    def emit(self, record: logging.LogRecord) -> None:
        """Capture a log record"""
        try:
            # Extract execution_id if present in the message
            execution_id = None
            msg = self.format(record)

            # Try to extract execution ID from message
            if 'execution' in msg.lower():
                import re
                match = re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', msg, re.IGNORECASE)
                if match:
                    execution_id = match.group(0)

            entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                level=record.levelname,
                logger=record.name,
                message=record.getMessage(),
                execution_id=execution_id,
            )

            with self._lock:
                self.logs.append(entry)

        except Exception:
            self.handleError(record)

    def get_logs(
        self,
        limit: int = 100,
        level: str | None = None,
        logger_filter: str | None = None,
        execution_id: str | None = None,
    ) -> list[dict]:
        """
        Get recent logs with optional filtering.

        Args:
            limit: Maximum number of logs to return
            level: Filter by log level (INFO, WARNING, ERROR, etc.)
            logger_filter: Filter by logger name (substring match)
            execution_id: Filter by execution ID

        Returns:
            List of log entries as dicts
        """
        with self._lock:
            logs = list(self.logs)

        # Apply filters
        if level:
            logs = [entry for entry in logs if entry.level == level.upper()]

        if logger_filter:
            logs = [entry for entry in logs if logger_filter.lower() in entry.logger.lower()]

        if execution_id:
            logs = [entry for entry in logs if entry.execution_id == execution_id]

        # Return most recent first, limited
        logs = list(reversed(logs))[:limit]

        return [asdict(entry) for entry in logs]

    def get_stats(self) -> dict:
        """Get log statistics"""
        with self._lock:
            logs = list(self.logs)

        level_counts = {}
        for log in logs:
            level_counts[log.level] = level_counts.get(log.level, 0) + 1

        return {
            "total_captured": len(logs),
            "max_entries": self.max_entries,
            "level_counts": level_counts,
            "oldest_entry": logs[0].timestamp if logs else None,
            "newest_entry": logs[-1].timestamp if logs else None,
        }

    def clear(self) -> None:
        """Clear all captured logs"""
        with self._lock:
            self.logs.clear()


# Global log capture handler instance
_log_capture_handler: LogCaptureHandler | None = None


def setup_log_capture(max_entries: int = 2000) -> LogCaptureHandler:
    """
    Set up log capture on the root logger.
    Call this once during app startup.

    Args:
        max_entries: Maximum log entries to keep in memory

    Returns:
        The LogCaptureHandler instance
    """
    global _log_capture_handler

    if _log_capture_handler is None:
        _log_capture_handler = LogCaptureHandler(max_entries=max_entries)
        _log_capture_handler.setLevel(logging.DEBUG)

        # Add to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(_log_capture_handler)

        # Also add to ignition_toolkit logger specifically
        toolkit_logger = logging.getLogger('ignition_toolkit')
        toolkit_logger.addHandler(_log_capture_handler)

    return _log_capture_handler


def get_log_capture() -> LogCaptureHandler | None:
    """Get the global log capture handler"""
    return _log_capture_handler

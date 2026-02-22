"""
Logs API Router

Provides endpoints to access backend logs from the UI.
"""

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ignition_toolkit.api.services.log_capture import get_log_capture

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["logs"])


class LogEntry(BaseModel):
    """Log entry response model"""
    timestamp: str
    level: str
    logger: str
    message: str
    execution_id: str | None = None


class LogsResponse(BaseModel):
    """Response containing log entries"""
    logs: list[LogEntry]
    total: int
    filtered: int


class LogStatsResponse(BaseModel):
    """Log statistics response"""
    total_captured: int
    max_entries: int
    level_counts: dict[str, int]
    oldest_entry: str | None
    newest_entry: str | None


@router.get("", response_model=LogsResponse)
async def get_logs(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of logs to return"),
    level: str | None = Query(default=None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)"),
    logger_filter: str | None = Query(default=None, description="Filter by logger name (substring match)"),
    execution_id: str | None = Query(default=None, description="Filter by execution ID"),
):
    """
    Get recent backend logs with optional filtering.

    Logs are returned in reverse chronological order (newest first).
    """
    capture = get_log_capture()

    if not capture:
        return LogsResponse(logs=[], total=0, filtered=0)

    logs = capture.get_logs(
        limit=limit,
        level=level,
        logger_filter=logger_filter,
        execution_id=execution_id,
    )

    stats = capture.get_stats()

    return LogsResponse(
        logs=[LogEntry(**log) for log in logs],
        total=stats["total_captured"],
        filtered=len(logs),
    )


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats():
    """Get log capture statistics"""
    capture = get_log_capture()

    if not capture:
        return LogStatsResponse(
            total_captured=0,
            max_entries=0,
            level_counts={},
            oldest_entry=None,
            newest_entry=None,
        )

    stats = capture.get_stats()
    return LogStatsResponse(**stats)


@router.get("/execution/{execution_id}", response_model=LogsResponse)
async def get_execution_logs(
    execution_id: str,
    limit: int = Query(default=500, ge=1, le=2000, description="Maximum number of logs to return"),
):
    """
    Get logs for a specific execution.

    Returns all logs that mention the given execution ID.
    """
    capture = get_log_capture()

    if not capture:
        return LogsResponse(logs=[], total=0, filtered=0)

    logs = capture.get_logs(
        limit=limit,
        execution_id=execution_id,
    )

    stats = capture.get_stats()

    return LogsResponse(
        logs=[LogEntry(**log) for log in logs],
        total=stats["total_captured"],
        filtered=len(logs),
    )


@router.delete("")
async def clear_logs():
    """Clear all captured logs"""
    capture = get_log_capture()

    if capture:
        capture.clear()
        logger.info("Logs cleared by user request")

    return {"message": "Logs cleared", "success": True}

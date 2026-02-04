"""
Health check endpoints

Provides Kubernetes-style health check endpoints for monitoring and debugging:
- GET /health - Overall health check (healthy/degraded/unhealthy)
- GET /health/live - Liveness probe (always 200 if running)
- GET /health/ready - Readiness probe (200 if ready, 503 if not)
- GET /health/detailed - Detailed component-level health information
- GET /health/database - Database statistics
- GET /health/storage - Screenshot storage statistics
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from ignition_toolkit import __version__
from ignition_toolkit.startup.health import HealthStatus, get_health_state
from ignition_toolkit.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(response: Response) -> dict[str, Any]:
    """
    Overall health check

    Returns:
        200: System is healthy or degraded (can serve requests)
        503: System is unhealthy (cannot serve requests)

    Response includes:
        - status: "healthy", "degraded", or "unhealthy"
        - ready: Boolean indicating if system is ready
        - errors: List of error messages (if unhealthy)
        - warnings: List of warning messages (if degraded)
    """
    health = get_health_state()

    # Return 503 if unhealthy, 200 otherwise
    if health.overall == HealthStatus.UNHEALTHY:
        response.status_code = 503

    return {
        "status": health.overall.value,
        "ready": health.ready,
        "version": __version__,
        "errors": health.errors if health.errors else None,
        "warnings": health.warnings if health.warnings else None,
    }


@router.get("/live")
async def liveness_probe() -> dict[str, str]:
    """
    Liveness probe (Kubernetes-style)

    Always returns 200 if the application is running.
    Used to detect if the application needs to be restarted.

    Returns:
        200: Application is running
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness_probe(response: Response) -> dict[str, Any]:
    """
    Readiness probe (Kubernetes-style)

    Returns 200 if system is ready to serve requests, 503 otherwise.
    Used to determine if traffic should be routed to this instance.

    Returns:
        200: System is ready to serve requests
        503: System is not ready (still starting up or degraded)
    """
    health = get_health_state()

    # Return 503 if not ready or unhealthy
    if not health.ready or health.overall == HealthStatus.UNHEALTHY:
        response.status_code = 503

    return {
        "ready": health.ready,
        "status": health.overall.value,
    }


@router.get("/detailed")
async def detailed_health(response: Response) -> dict[str, Any]:
    """
    Detailed health check with component-level information

    Returns comprehensive health information including:
    - Overall system health
    - Individual component health (database, vault, playbooks, frontend)
    - Startup time
    - Errors and warnings

    Returns:
        200: System is healthy or degraded
        503: System is unhealthy
    """
    health = get_health_state()

    # Return 503 if unhealthy
    if health.overall == HealthStatus.UNHEALTHY:
        response.status_code = 503

    return health.to_dict()


@router.get("/database")
async def database_health() -> dict[str, Any]:
    """
    Database statistics and health

    Returns information about the SQLite database:
    - File size
    - Execution count
    - Step result count
    - Oldest/newest execution timestamps

    Returns:
        200: Database statistics
    """
    db = get_database()
    stats: dict[str, Any] = {
        "status": "healthy",
        "type": "sqlite",
    }

    try:
        # Get database file size
        if db and hasattr(db, 'db_path'):
            db_path = Path(db.db_path)
            if db_path.exists():
                size_bytes = db_path.stat().st_size
                stats["file_size_bytes"] = size_bytes
                stats["file_size_mb"] = round(size_bytes / (1024 * 1024), 2)
                stats["file_path"] = str(db_path)

        # Get execution statistics
        if db:
            with db.session_scope() as session:
                from ignition_toolkit.storage.models import ExecutionModel, StepResultModel
                from sqlalchemy import func

                # Count executions
                execution_count = session.query(func.count(ExecutionModel.id)).scalar()
                stats["execution_count"] = execution_count

                # Count step results
                step_count = session.query(func.count(StepResultModel.id)).scalar()
                stats["step_result_count"] = step_count

                # Get oldest and newest execution
                oldest = session.query(func.min(ExecutionModel.started_at)).scalar()
                newest = session.query(func.max(ExecutionModel.started_at)).scalar()

                if oldest:
                    stats["oldest_execution"] = oldest.isoformat()
                if newest:
                    stats["newest_execution"] = newest.isoformat()

                # Count by status
                status_counts = (
                    session.query(ExecutionModel.status, func.count(ExecutionModel.id))
                    .group_by(ExecutionModel.status)
                    .all()
                )
                stats["executions_by_status"] = {status: count for status, count in status_counts}

    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        stats["status"] = "error"
        stats["error"] = str(e)

    return stats


@router.get("/storage")
async def storage_health() -> dict[str, Any]:
    """
    Screenshot storage statistics

    Returns information about screenshot storage:
    - Directory path
    - Total size
    - File count
    - Oldest/newest screenshots

    Returns:
        200: Storage statistics
    """
    from ignition_toolkit.core.paths import get_screenshots_dir

    stats: dict[str, Any] = {
        "status": "healthy",
        "type": "filesystem",
    }

    try:
        screenshots_dir = get_screenshots_dir()
        stats["directory"] = str(screenshots_dir)

        if screenshots_dir.exists():
            # Count files and calculate total size
            total_size = 0
            file_count = 0
            oldest_time = None
            newest_time = None

            for file_path in screenshots_dir.rglob("*.png"):
                file_count += 1
                stat = file_path.stat()
                total_size += stat.st_size

                mtime = stat.st_mtime
                if oldest_time is None or mtime < oldest_time:
                    oldest_time = mtime
                if newest_time is None or mtime > newest_time:
                    newest_time = mtime

            # Also count jpg files
            for file_path in screenshots_dir.rglob("*.jpg"):
                file_count += 1
                stat = file_path.stat()
                total_size += stat.st_size

                mtime = stat.st_mtime
                if oldest_time is None or mtime < oldest_time:
                    oldest_time = mtime
                if newest_time is None or mtime > newest_time:
                    newest_time = mtime

            stats["file_count"] = file_count
            stats["total_size_bytes"] = total_size
            stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)

            if oldest_time:
                from datetime import datetime
                stats["oldest_screenshot"] = datetime.fromtimestamp(oldest_time).isoformat()
            if newest_time:
                from datetime import datetime
                stats["newest_screenshot"] = datetime.fromtimestamp(newest_time).isoformat()
        else:
            stats["file_count"] = 0
            stats["total_size_bytes"] = 0
            stats["total_size_mb"] = 0
            stats["note"] = "Screenshots directory does not exist yet"

    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        stats["status"] = "error"
        stats["error"] = str(e)

    return stats


class CleanupRequest(BaseModel):
    """Request for cleanup operation"""
    older_than_days: int = 30
    dry_run: bool = True


@router.post("/cleanup")
async def cleanup_old_data(request: CleanupRequest) -> dict[str, Any]:
    """
    Clean up old executions and screenshots

    Removes executions and their associated screenshots older than the specified
    number of days. Use dry_run=true (default) to preview what would be deleted.

    Args:
        older_than_days: Delete data older than this many days (default: 30)
        dry_run: If true, only report what would be deleted without actually deleting

    Returns:
        Summary of deleted (or would-be-deleted) items
    """
    from datetime import datetime, timedelta
    from ignition_toolkit.api.routers.executions.helpers import (
        extract_screenshot_paths,
        delete_screenshot_files,
    )

    db = get_database()
    cutoff_date = datetime.now() - timedelta(days=request.older_than_days)

    result: dict[str, Any] = {
        "dry_run": request.dry_run,
        "older_than_days": request.older_than_days,
        "cutoff_date": cutoff_date.isoformat(),
        "executions_found": 0,
        "executions_deleted": 0,
        "screenshots_found": 0,
        "screenshots_deleted": 0,
        "space_freed_mb": 0,
    }

    try:
        with db.session_scope() as session:
            from ignition_toolkit.storage.models import ExecutionModel, StepResultModel

            # Find old executions
            old_executions = (
                session.query(ExecutionModel)
                .filter(ExecutionModel.started_at < cutoff_date)
                .all()
            )

            result["executions_found"] = len(old_executions)

            all_screenshot_paths = []
            for execution in old_executions:
                # Collect screenshot paths from step results
                screenshot_paths = extract_screenshot_paths(execution.step_results)
                all_screenshot_paths.extend(screenshot_paths)

            result["screenshots_found"] = len(all_screenshot_paths)

            # Calculate space that would be freed
            total_size = 0
            for path in all_screenshot_paths:
                if path.exists():
                    total_size += path.stat().st_size
            result["space_freed_mb"] = round(total_size / (1024 * 1024), 2)

            if not request.dry_run:
                # Actually delete the data
                for execution in old_executions:
                    # Delete step results first
                    session.query(StepResultModel).filter(
                        StepResultModel.execution_id == execution.execution_id
                    ).delete()

                    # Delete execution
                    session.delete(execution)

                result["executions_deleted"] = len(old_executions)

                # Delete screenshot files
                deleted_count = delete_screenshot_files(all_screenshot_paths)
                result["screenshots_deleted"] = deleted_count

                logger.info(
                    f"Cleanup completed: deleted {len(old_executions)} executions "
                    f"and {deleted_count} screenshots"
                )

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

    return result

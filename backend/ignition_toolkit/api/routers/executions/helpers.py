"""
Helper functions and utilities for execution management

Contains:
- ExecutionContext dataclass for managing execution state
- Dependency injection functions
- Helper functions for playbook execution
- Background task functions
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable

from fastapi import HTTPException

from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.storage import get_database

if TYPE_CHECKING:
    from ignition_toolkit.gateway.client import GatewayClient
    from ignition_toolkit.playbook.models import Playbook

logger = logging.getLogger(__name__)

# Execution Configuration Constants
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 3600  # 1 hour
DEFAULT_EXECUTION_LIST_LIMIT = 50


# ============================================================================
# ExecutionContext - Encapsulates execution-related global state
# ============================================================================


@dataclass
class ExecutionContext:
    """Encapsulates all execution-related global state"""

    active_engines: dict[str, PlaybookEngine]
    active_tasks: dict[str, asyncio.Task]
    completion_times: dict[str, datetime]
    ttl_minutes: int

    def get_engine(self, execution_id: str) -> PlaybookEngine | None:
        """Get engine by execution ID"""
        return self.active_engines.get(execution_id)

    def add_engine(self, execution_id: str, engine: PlaybookEngine, task: asyncio.Task) -> None:
        """Register new execution"""
        self.active_engines[execution_id] = engine
        self.active_tasks[execution_id] = task

    def remove_engine(self, execution_id: str) -> None:
        """Remove completed execution"""
        self.active_engines.pop(execution_id, None)
        self.active_tasks.pop(execution_id, None)
        self.completion_times[execution_id] = datetime.now()

    def is_expired(self, execution_id: str) -> bool:
        """Check if execution has exceeded TTL"""
        if completion_time := self.completion_times.get(execution_id):
            elapsed_minutes = (datetime.now() - completion_time).total_seconds() / 60
            return elapsed_minutes > self.ttl_minutes
        return False


# ============================================================================
# Dependency injection functions
# ============================================================================


def get_execution_context() -> ExecutionContext:
    """Get execution context from app state"""
    from ignition_toolkit.api.app import (
        EXECUTION_TTL_MINUTES,
        active_engines,
        active_tasks,
        engine_completion_times,
    )

    return ExecutionContext(
        active_engines=active_engines,
        active_tasks=active_tasks,
        completion_times=engine_completion_times,
        ttl_minutes=EXECUTION_TTL_MINUTES,
    )


# Legacy getter functions (to be replaced gradually)
def get_active_engines():
    """Get shared active engines dict from app"""
    return get_execution_context().active_engines


def get_active_tasks():
    """Get shared active tasks dict from app"""
    return get_execution_context().active_tasks


def get_engine_completion_times():
    """Get shared engine completion times dict from app"""
    return get_execution_context().completion_times


def get_execution_ttl_minutes():
    """Get execution TTL configuration from app"""
    return get_execution_context().ttl_minutes


async def get_engine_or_404(execution_id: str) -> PlaybookEngine:
    """
    FastAPI dependency to retrieve active engine or raise 404

    Args:
        execution_id: Execution UUID from path parameter (shared with endpoint)

    Returns:
        Active PlaybookEngine instance

    Raises:
        HTTPException: 404 if execution not found or not active
    """
    # Lazy import to avoid circular dependency
    from ignition_toolkit.api.app import app

    # Use the new service layer architecture
    if not hasattr(app.state, "services"):
        raise HTTPException(
            status_code=503,
            detail="Application services not initialized",
        )

    engine = app.state.services.execution_manager.get_engine(execution_id)

    if engine is None:
        raise HTTPException(
            status_code=404,
            detail=f"Execution {execution_id} not found or not active"
        )

    return engine


def get_execution_manager():
    """Get ExecutionManager from service layer (lazy import to avoid circular dependency)"""
    from ignition_toolkit.api.app import app

    if not hasattr(app.state, "services"):
        raise RuntimeError("Application services not initialized")

    return app.state.services.execution_manager


# ============================================================================
# Path validation helpers
# ============================================================================


def validate_and_resolve_playbook_path(playbook_relative_path_str: str) -> tuple[Path, Path]:
    """
    Validate playbook path and resolve to absolute path

    Args:
        playbook_relative_path_str: Relative path to playbook file

    Returns:
        Tuple of (playbooks_dir, full_playbook_path)

    Raises:
        HTTPException: If path is invalid or file not found
    """
    from ignition_toolkit.core.paths import get_all_playbook_dirs

    playbook_relative_path = Path(playbook_relative_path_str)

    # Security check - prevent directory traversal
    if ".." in str(playbook_relative_path) or playbook_relative_path.is_absolute():
        raise HTTPException(
            status_code=400,
            detail="Invalid playbook path - relative paths only, no directory traversal",
        )

    # Search all playbook directories (user first, then built-in)
    for playbooks_dir in get_all_playbook_dirs():
        playbook_path = playbooks_dir / playbook_relative_path
        if playbook_path.exists():
            return playbooks_dir, playbook_path

    raise HTTPException(
        status_code=404, detail=f"Playbook file not found: {playbook_relative_path_str}"
    )


# ============================================================================
# Execution runner and timeout watchdog
# ============================================================================


def create_execution_runner(
    engine: PlaybookEngine,
    playbook: "Playbook",
    parameters: dict,
    playbook_path: Path,
    execution_id: str,
    gateway_client: "GatewayClient | None",
) -> Callable[[], Awaitable[None]]:
    """
    Create async function that runs the playbook execution

    Args:
        engine: PlaybookEngine instance
        playbook: Loaded playbook object
        parameters: Execution parameters
        playbook_path: Path to playbook file
        execution_id: Execution UUID
        gateway_client: Optional Gateway client

    Returns:
        Async function that executes the playbook
    """
    from ignition_toolkit.api.app import app

    async def run_execution():
        """Execute playbook in background"""
        logger.debug("Starting background execution for {execution_id}")
        start_time = datetime.now()
        try:
            logger.debug("Entering gateway client context")
            if gateway_client:
                await gateway_client.__aenter__()

            logger.debug("Calling engine.execute_playbook")
            execution_state = await engine.execute_playbook(
                playbook,
                parameters,
                base_path=playbook_path.parent,
                execution_id=execution_id,
                playbook_path=playbook_path,
            )
            logger.debug("engine.execute_playbook returned")

            logger.info(
                f"Execution {execution_state.execution_id} completed with status: {execution_state.status}"
            )

            # Mark completion time for TTL cleanup
            engine_completion_times = get_engine_completion_times()
            engine_completion_times[execution_id] = datetime.now()

        except asyncio.CancelledError:
            logger.warning(f"Execution {execution_id} was cancelled")
            # Mark completion time even for cancelled executions
            engine_completion_times = get_engine_completion_times()
            engine_completion_times[execution_id] = datetime.now()

            # Update database to mark execution as cancelled
            db = get_database()
            if db:
                with db.session_scope() as session:
                    from ignition_toolkit.storage import ExecutionModel

                    execution = (
                        session.query(ExecutionModel)
                        .filter_by(execution_id=execution_id)
                        .first()
                    )
                    if execution:
                        execution.status = "cancelled"
                        execution.completed_at = datetime.now()
                        session.commit()
                        logger.info(
                            f"Updated execution {execution_id} status to 'cancelled' in database"
                        )

                        # Broadcast cancellation to WebSocket clients
                        from ignition_toolkit.playbook.models import ExecutionStatus

                        # Get current execution state and update status
                        execution_state = engine.get_current_execution()
                        if execution_state:
                            execution_state.status = ExecutionStatus.CANCELLED
                            execution_state.completed_at = datetime.now()

                            # Use WebSocketManager from app services
                            websocket_manager = app.state.services.websocket_manager
                            await websocket_manager.broadcast_execution_state(execution_state)
                            logger.info(
                                f"Broadcasted cancellation status via WebSocket for {execution_id}"
                            )

            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            logger.exception(f"Error in execution {execution_id}: {e}")
            # Mark completion time for failed executions
            engine_completion_times = get_engine_completion_times()
            engine_completion_times[execution_id] = datetime.now()

            # Update database to mark execution as failed
            db = get_database()
            if db:
                with db.session_scope() as session:
                    from ignition_toolkit.storage import ExecutionModel

                    execution = (
                        session.query(ExecutionModel)
                        .filter_by(execution_id=execution_id)
                        .first()
                    )
                    if execution and execution.status in ("running", "paused"):
                        execution.status = "failed"
                        execution.completed_at = datetime.now()
                        execution.error_message = str(e)[:500]
                        session.commit()
                        logger.info(
                            f"Updated execution {execution_id} status to 'failed' in database"
                        )

                        # Broadcast failure to WebSocket clients
                        from ignition_toolkit.playbook.models import ExecutionStatus

                        execution_state = engine.get_current_execution()
                        if execution_state:
                            execution_state.status = ExecutionStatus.FAILED
                            execution_state.completed_at = datetime.now()
                            execution_state.error = str(e)[:500]

                            websocket_manager = app.state.services.websocket_manager
                            await websocket_manager.broadcast_execution_state(
                                execution_state
                            )
                            logger.info(
                                f"Broadcasted failure status via WebSocket for {execution_id}"
                            )
        finally:
            if gateway_client:
                await gateway_client.__aexit__(None, None, None)
            # NOTE: Task cleanup is handled by TTL mechanism, not here
            # Removing task too early prevents cancel endpoint from finding it

    return run_execution


def create_timeout_watchdog(
    execution_id: str, task: asyncio.Task, engine: PlaybookEngine
) -> Callable[[], Awaitable[None]]:
    """
    Create timeout watchdog that auto-cancels long-running executions

    Args:
        execution_id: Execution UUID
        task: Asyncio task to monitor
        engine: PlaybookEngine to cancel

    Returns:
        Async function that monitors execution timeout
    """

    async def timeout_watchdog():
        """Cancel execution if it runs longer than configured timeout"""
        try:
            await asyncio.sleep(DEFAULT_EXECUTION_TIMEOUT_SECONDS)
            if not task.done():
                logger.warning(
                    f"Execution {execution_id} exceeded timeout - auto-cancelling"
                )
                await engine.cancel()
                task.cancel()
        except asyncio.CancelledError:
            pass  # Watchdog cancelled (normal if execution finishes)
        except Exception as e:
            logger.exception(f"Error in timeout watchdog for {execution_id}: {e}")

    return timeout_watchdog


# ============================================================================
# Screenshot management helpers
# ============================================================================


def extract_screenshot_paths(step_results: list) -> list[Path]:
    """
    Extract screenshot file paths from step results

    Args:
        step_results: List of StepResultModel objects

    Returns:
        List of Path objects for screenshots found in step results
    """
    screenshot_paths = []

    for step in step_results:
        # Check output field for single screenshot (browser.screenshot steps)
        if step.output and isinstance(step.output, dict):
            screenshot = step.output.get("screenshot")
            if screenshot and isinstance(screenshot, str):
                screenshot_paths.append(Path(screenshot))

            # Check for screenshot arrays from nested playbook executions (playbook.run steps)
            screenshots = step.output.get("screenshots", [])
            if isinstance(screenshots, list):
                screenshot_paths.extend([Path(s) for s in screenshots if isinstance(s, str)])

        # Also check artifacts field for screenshot arrays (future use)
        if step.artifacts and isinstance(step.artifacts, dict):
            # artifacts may contain: {"screenshots": ["/path/to/file.png", ...]}
            screenshots = step.artifacts.get("screenshots", [])
            if isinstance(screenshots, list):
                screenshot_paths.extend([Path(s) for s in screenshots if isinstance(s, str)])

    return screenshot_paths


def delete_screenshot_files(screenshot_paths: list[Path]) -> int:
    """
    Delete screenshot files from filesystem

    Args:
        screenshot_paths: List of Path objects to delete

    Returns:
        Number of files successfully deleted
    """
    deleted_count = 0

    for screenshot_path in screenshot_paths:
        try:
            if screenshot_path.exists():
                screenshot_path.unlink()
                deleted_count += 1
                logger.info(f"Deleted screenshot: {screenshot_path.name}")
        except Exception as e:
            logger.warning(f"Failed to delete screenshot {screenshot_path}: {e}")

    return deleted_count


# ============================================================================
# Background Tasks
# ============================================================================


async def cleanup_old_executions():
    """Remove completed executions older than TTL from memory"""
    active_engines = get_active_engines()
    active_tasks = get_active_tasks()
    engine_completion_times = get_engine_completion_times()
    ttl_minutes = get_execution_ttl_minutes()

    current_time = datetime.now()
    ttl_delta = timedelta(minutes=ttl_minutes)
    to_remove = []

    for exec_id, completion_time in engine_completion_times.items():
        if current_time - completion_time > ttl_delta:
            to_remove.append(exec_id)

    for exec_id in to_remove:
        if exec_id in active_engines:
            logger.info(f"Removing execution {exec_id} (TTL expired)")
            del active_engines[exec_id]
        if exec_id in active_tasks:
            del active_tasks[exec_id]
        del engine_completion_times[exec_id]

    if to_remove:
        logger.info(f"Cleaned up {len(to_remove)} old execution(s)")

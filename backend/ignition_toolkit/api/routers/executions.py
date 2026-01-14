"""
Execution management routes

Handles playbook execution control, status tracking, and lifecycle management.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path as PathParam
from pydantic import BaseModel

from ignition_toolkit.api.routers.models import (
    ExecutionRequest,
    ExecutionResponse,
    ExecutionStatusResponse,
    StepResultResponse,
)
from ignition_toolkit.api.services.execution_response_builder import ExecutionResponseBuilder
from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.playbook.models import ExecutionState, StepResult
from ignition_toolkit.storage import get_database
from ignition_toolkit.storage.models import ExecutionModel

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/executions", tags=["executions"])

# Execution Configuration Constants
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 3600  # 1 hour
DEFAULT_EXECUTION_LIST_LIMIT = 50


# Execution Context Dataclass
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


# Dependency injection for global state
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
# Helper Functions
# ============================================================================
# Note: Helper functions moved to services/execution_response_builder.py
# ============================================================================
# Pydantic Models (shared models imported from models.py)
# ============================================================================


class PlaybookCodeUpdateRequest(BaseModel):
    """Request to update playbook code during execution"""

    code: str


# ============================================================================
# Helper Functions for start_execution
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
    from ignition_toolkit.core.paths import get_playbooks_dir

    playbook_relative_path = Path(playbook_relative_path_str)

    # Security check - prevent directory traversal
    if ".." in str(playbook_relative_path) or playbook_relative_path.is_absolute():
        raise HTTPException(
            status_code=400,
            detail="Invalid playbook path - relative paths only, no directory traversal",
        )

    # Resolve full path relative to playbooks directory
    playbooks_dir = get_playbooks_dir()
    playbook_path = playbooks_dir / playbook_relative_path

    if not playbook_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Playbook file not found: {playbook_relative_path_str}"
        )

    return playbooks_dir, playbook_path



def create_execution_runner(
    engine: PlaybookEngine,
    playbook: "Playbook",
    parameters: dict,
    playbook_path: Path,
    execution_id: str,
    gateway_client: "GatewayClient | None",
) -> "Callable[[], Awaitable[None]]":
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
        finally:
            if gateway_client:
                await gateway_client.__aexit__(None, None, None)
            # NOTE: Task cleanup is handled by TTL mechanism, not here
            # Removing task too early prevents cancel endpoint from finding it

    return run_execution


def create_timeout_watchdog(
    execution_id: str, task: asyncio.Task, engine: PlaybookEngine
) -> "Callable[[], Awaitable[None]]":
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


# ============================================================================
# Routes
# ============================================================================


@router.post("", response_model=ExecutionResponse)
async def start_execution(request: ExecutionRequest, background_tasks: BackgroundTasks):
    """
    Start playbook execution

    Simplified implementation using ExecutionService (replaces 11-step process with 3 lines).
    """
    from ignition_toolkit.api.dependencies import get_services
    from ignition_toolkit.playbook.loader import PlaybookLoader

    try:
        # Get services from app state
        # Note: We can't use Depends() here without refactoring to accept Request parameter
        # For now, get services directly from app (will refactor in next iteration)
        from ignition_toolkit.api.app import app

        if not hasattr(app.state, "services"):
            raise HTTPException(
                status_code=503,
                detail="Application services not initialized",
            )

        services = app.state.services

        # Start execution using service layer (replaces 100+ lines of boilerplate)
        execution_id = await services.execution_service.start_execution(
            playbook_path=request.playbook_path,
            parameters=request.parameters,
            gateway_url=request.gateway_url,
            credential_name=request.credential_name,
            debug_mode=request.debug_mode,
            timeout_seconds=3600,  # 1 hour
            timeout_overrides=request.timeout_overrides,
        )

        # Load playbook for response (TODO: return from service)
        from ignition_toolkit.core.validation import PathValidator

        _, playbook_path = PathValidator.validate_and_resolve(request.playbook_path)
        playbook = PlaybookLoader.load_from_file(playbook_path)

        # Schedule cleanup background task
        background_tasks.add_task(services.execution_manager.cleanup_expired)

        return ExecutionResponse(
            execution_id=execution_id,
            playbook_name=playbook.name,
            status="started",
            message=f"Execution started with ID: {execution_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[ExecutionStatusResponse])
async def list_executions(limit: int = DEFAULT_EXECUTION_LIST_LIMIT, status: str | None = None):
    """List all executions (active + recent completed from database)"""
    active_engines = get_active_engines()
    db = get_database()

    executions = []

    # Add active executions
    for exec_id, engine in active_engines.items():
        state = engine.get_current_execution()
        if not state:
            continue

        executions.append(ExecutionResponseBuilder.from_engine(exec_id, engine))

    # Add recent completed executions from database
    try:
        with db.session_scope() as session:
            from ignition_toolkit.storage.models import ExecutionModel

            query = session.query(ExecutionModel).order_by(ExecutionModel.started_at.desc())

            if status:
                query = query.filter(ExecutionModel.status == status)

            db_executions = query.limit(limit).all()
            logger.info(f"Loaded {len(db_executions)} executions from database")

            for db_exec in db_executions:
                # Load step results from database relationship
                step_results = [
                    StepResultResponse(
                        step_id=step.step_id,
                        step_name=step.step_name,
                        status=step.status,
                        error=step.error_message,
                        started_at=step.started_at,
                        completed_at=step.completed_at,
                        output=step.output,
                    )
                    for step in db_exec.step_results
                ]

                executions.append(ExecutionResponseBuilder.from_database(db_exec))
    except Exception as e:
        logger.exception(f"Error loading executions from database: {e}")

    return executions[:limit]


@router.get("/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str):
    """Get execution status and step results"""
    active_engines = get_active_engines()

    if execution_id in active_engines:
        engine = active_engines[execution_id]
        state = engine.get_current_execution()

        if state:
            # Engine has active state, return it
            return ExecutionResponseBuilder.from_engine(execution_id, engine)

    # Try to load from database
    db = get_database()
    try:
        with db.session_scope() as session:
            from ignition_toolkit.storage.models import ExecutionModel

            execution = (
                session.query(ExecutionModel)
                .filter(ExecutionModel.execution_id == execution_id)
                .first()
            )

            if execution:
                # Load step results from database relationship
                step_results = [
                    StepResultResponse(
                        step_id=step.step_id,
                        step_name=step.step_name,
                        status=step.status,
                        error=step.error_message,
                        started_at=step.started_at,
                        completed_at=step.completed_at,
                        output=step.output,
                    )
                    for step in execution.step_results
                ]

                # Extract domain from execution metadata
                domain = None
                if execution.execution_metadata:
                    domain = execution.execution_metadata.get("domain")

                return ExecutionStatusResponse(
                    execution_id=execution.execution_id,
                    playbook_name=execution.playbook_name,
                    status=execution.status,
                    started_at=execution.started_at,
                    completed_at=execution.completed_at,
                    current_step_index=len(step_results),
                    total_steps=len(step_results),
                    error=execution.error_message,
                    debug_mode=execution.execution_metadata.get("debug_mode", False) if execution.execution_metadata else False,
                    step_results=step_results,
                    domain=domain,
                )
    except Exception as e:
        logger.error(f"Error loading execution from database: {e}")

    raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")


@router.get("/{execution_id}/status", response_model=ExecutionStatusResponse)
async def get_execution_status_with_path(execution_id: str):
    """Get execution status (alternate endpoint for compatibility)"""
    return await get_execution_status(execution_id)


@router.post("/{execution_id}/pause")
async def pause_execution(execution_id: str, engine: PlaybookEngine = Depends(get_engine_or_404)):
    """Pause execution"""
    engine.pause()
    return {"message": "Execution paused", "execution_id": execution_id}


@router.post("/{execution_id}/resume")
async def resume_execution(execution_id: str, engine: PlaybookEngine = Depends(get_engine_or_404)):
    """Resume paused execution"""
    await engine.resume()
    return {"message": "Execution resumed", "execution_id": execution_id}


@router.post("/{execution_id}/skip")
async def skip_step(execution_id: str, engine: PlaybookEngine = Depends(get_engine_or_404)):
    """Skip current step and move to next"""
    await engine.skip_current_step()
    return {"message": "Step skipped", "execution_id": execution_id}


@router.post("/{execution_id}/skip_back")
async def skip_back_step(execution_id: str, engine: PlaybookEngine = Depends(get_engine_or_404)):
    """Skip back to previous step"""
    await engine.skip_back_step()
    return {"message": "Skipped back to previous step", "execution_id": execution_id}


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """Cancel execution"""
    from ignition_toolkit.api.app import app

    # Get execution manager from app services
    if not hasattr(app.state, "services"):
        raise HTTPException(
            status_code=503,
            detail="Application services not initialized",
        )

    execution_manager = app.state.services.execution_manager

    # Try to cancel active execution using ExecutionManager
    cancelled = await execution_manager.cancel_execution(execution_id)

    if cancelled:
        logger.info(f"✅ Successfully cancelled execution {execution_id}")
        return {"message": "Execution cancelled", "execution_id": execution_id}

    # Execution not in memory - check if it exists in database (old execution from before server restart)
    db = get_database()
    if not db:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

    with db.session_scope() as session:
        from ignition_toolkit.storage import ExecutionModel

        execution = (
            session.query(ExecutionModel)
            .filter_by(execution_id=execution_id)
            .first()
        )

        if not execution:
            raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

        # Mark old execution as cancelled in database
        if execution.status in ["running", "paused"]:
            logger.info(f"Cancelling database-only execution {execution_id} (started {execution.started_at})")
            execution.status = "cancelled"
            execution.completed_at = datetime.now()
            execution.error_message = "Cancelled by user (execution was from before server restart)"
            session.commit()
            logger.info(f"Database-only execution {execution_id} marked as cancelled")
            return {"message": "Execution marked as cancelled in database", "execution_id": execution_id}
        else:
            # Execution already completed - return success instead of error for better UX
            logger.info(f"Cancel requested for already-completed execution {execution_id} (status: {execution.status})")
            return {
                "message": f"Execution already completed with status: {execution.status}",
                "execution_id": execution_id,
                "already_completed": True
            }


@router.get("/{execution_id}/playbook/code")
async def get_playbook_code(execution_id: str, engine: PlaybookEngine = Depends(get_engine_or_404)):
    """Get the YAML code for the playbook being executed"""
    # Read the original playbook file
    playbook_path = engine.get_playbook_path()
    if not playbook_path or not playbook_path.exists():
        raise HTTPException(status_code=404, detail="Playbook file not found")

    yaml_content = playbook_path.read_text()

    state = engine.get_current_execution()
    playbook_name = state.playbook_name if state else "Unknown"

    return {
        "execution_id": execution_id,  # Use execution_id from path parameter
        "playbook_path": str(playbook_path),
        "playbook_name": playbook_name,
        "code": yaml_content,  # Frontend expects 'code' field
    }


@router.put("/{execution_id}/playbook/code")
async def update_playbook_code(
    execution_id: str,
    request: PlaybookCodeUpdateRequest,
    engine: PlaybookEngine = Depends(get_engine_or_404)
):
    """Update the playbook YAML during execution (for AI fixes)"""

    # Get playbook path
    playbook_path = engine.get_playbook_path()
    if not playbook_path or not playbook_path.exists():
        raise HTTPException(status_code=404, detail="Playbook file not found")

    # Validate YAML
    import yaml

    try:
        yaml.safe_load(request.code)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")

    # Create backup
    backup_path = playbook_path.with_suffix(
        f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    )
    backup_path.write_text(playbook_path.read_text())
    logger.info(f"Created backup: {backup_path}")

    # Write new content
    playbook_path.write_text(request.code)
    logger.info(f"Updated playbook code: {playbook_path}")

    return {
        "message": "Playbook code updated",
        "execution_id": execution_id,  # Use execution_id from path parameter
        "playbook_path": str(playbook_path),
        "backup_path": str(backup_path.name),
    }


@router.delete("/{execution_id}")
async def delete_execution(execution_id: str):
    """
    Delete execution from database and clean up related screenshots

    This removes:
    - Execution record from database
    - All step results for the execution
    - Screenshots captured during the execution
    """
    active_engines = get_active_engines()
    db = get_database()

    # Check if execution is still active - only block deletion if execution is actually running/paused
    if execution_id in active_engines:
        engine = active_engines[execution_id]
        state = engine.get_current_execution()
        if state and state.status in ["running", "paused"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete active execution. Cancel or wait for completion first.",
            )

    # Delete from database
    try:
        with db.session_scope() as session:
            from ignition_toolkit.storage.models import ExecutionModel, StepResultModel

            execution = (
                session.query(ExecutionModel)
                .filter(ExecutionModel.execution_id == execution_id)
                .first()
            )

            if not execution:
                raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

            # FIRST: Get screenshot paths from step results BEFORE deletion
            # Use SQLAlchemy relationship instead of query (execution_id is UUID string, not DB integer)
            step_results = execution.step_results
            screenshot_paths = extract_screenshot_paths(step_results)

            # NOTE: extract_screenshot_paths now handles nested playbook screenshots automatically
            # because playbook.run steps include a "screenshots" array in their output containing
            # all screenshots created during nested execution (supports up to depth 3 nesting)

            logger.info(f"Collected {len(screenshot_paths)} total screenshot paths (including nested playbooks)")

            # THEN: Delete related step results
            session.query(StepResultModel).filter(
                StepResultModel.execution_id == execution_id
            ).delete()

            # Delete execution
            session.delete(execution)
            logger.info(f"Deleted execution {execution_id} from database")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting execution from database: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Clean up screenshots from step results artifacts
    deleted_screenshots = delete_screenshot_files(screenshot_paths)

    return {
        "message": "Execution deleted successfully",
        "execution_id": execution_id,
        "screenshots_deleted": deleted_screenshots,
    }


@router.post("/{execution_id}/debug/enable")
async def enable_debug_mode(execution_id: str, engine: PlaybookEngine = Depends(get_engine_or_404)):
    """Enable debug mode for an active execution"""
    # Lazy import to avoid circular dependency
    from ignition_toolkit.api.app import app

    engine.state_manager.enable_debug_mode()

    logger.info(f"Debug mode enabled for execution {execution_id}")

    # Broadcast state update to WebSocket clients
    execution_state = engine.get_current_execution()
    if execution_state:
        # Update debug_mode flag in execution state
        execution_state.debug_mode = True
        # Use WebSocketManager from app services
        websocket_manager = app.state.services.websocket_manager
        await websocket_manager.broadcast_execution_state(execution_state)

    return {
        "status": "success",
        "execution_id": execution_id,
        "debug_mode": True,
        "message": "Debug mode enabled - execution will pause on next failure"
    }


@router.post("/{execution_id}/debug/disable")
async def disable_debug_mode(execution_id: str, engine: PlaybookEngine = Depends(get_engine_or_404)):
    """Disable debug mode for an active execution"""
    # Lazy import to avoid circular dependency
    from ignition_toolkit.api.app import app

    engine.state_manager.disable_debug_mode()

    logger.info(f"Debug mode disabled for execution {execution_id}")

    # Broadcast state update to WebSocket clients
    execution_state = engine.get_current_execution()
    if execution_state:
        # Update debug_mode flag in execution state
        execution_state.debug_mode = False
        # Use WebSocketManager from app services
        websocket_manager = app.state.services.websocket_manager
        await websocket_manager.broadcast_execution_state(execution_state)

    return {
        "status": "success",
        "execution_id": execution_id,
        "debug_mode": False,
        "message": "Debug mode disabled"
    }


class BrowserClickRequest(BaseModel):
    """Request to click at coordinates in browser"""

    x: int
    y: int


@router.post("/{execution_id}/browser/click")
async def click_in_browser(
    request: BrowserClickRequest,
    engine: PlaybookEngine = Depends(get_engine_or_404)
):
    """
    Click at specific coordinates in the browser during execution

    This allows users to interact with the browser during paused executions
    to help with debugging or manual intervention.

    Args:
        request: Browser click request with x and y coordinates
        engine: Active PlaybookEngine instance (injected)

    Returns:
        Success response with click coordinates

    Raises:
        HTTPException: If no browser available or click fails
    """
    # Check if browser manager exists
    if not engine.get_browser_manager():
        raise HTTPException(
            status_code=400, detail="No browser manager available for this execution"
        )

    try:
        # Perform click at coordinates
        await engine.get_browser_manager().click_at_coordinates(request.x, request.y)

        # Get execution state for execution_id
        state = engine.get_current_execution()
        execution_id = state.execution_id if state else "unknown"

        logger.info(
            f"Browser click executed at ({request.x}, {request.y}) for execution {execution_id}"
        )

        return {
            "status": "success",
            "message": f"Clicked at coordinates ({request.x}, {request.y})",
            "execution_id": execution_id,
            "coordinates": {"x": request.x, "y": request.y},
        }
    except Exception as e:
        logger.exception(f"Error clicking in browser: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to click in browser: {str(e)}"
        )

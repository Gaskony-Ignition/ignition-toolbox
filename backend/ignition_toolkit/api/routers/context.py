"""
Context API Router

Provides project context for AI assistants (Toolbox Assistant).
Returns comprehensive information about playbooks, executions, credentials,
logs, and system status.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ignition_toolkit.api.services.log_capture import get_log_capture
from ignition_toolkit.credentials import CredentialVault
from ignition_toolkit.storage import get_database

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/context", tags=["context"])


# ============================================================================
# Pydantic Models
# ============================================================================


class PlaybookSummary(BaseModel):
    """Summary of a playbook for AI context"""

    name: str
    description: str | None = None
    domain: str | None = None
    step_count: int = 0
    path: str


class StepResultSummary(BaseModel):
    """Summary of a step result"""

    step_name: str
    status: str
    error: str | None = None
    duration_seconds: float | None = None


class ExecutionSummary(BaseModel):
    """Summary of an execution for AI context"""

    execution_id: str
    playbook_name: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    step_results: list[StepResultSummary] = []
    parameters: dict[str, Any] | None = None


class CredentialSummary(BaseModel):
    """Summary of a credential (names only, no secrets)"""

    name: str
    has_gateway_url: bool = False
    gateway_url: str | None = None


class CloudDesignerSummary(BaseModel):
    """CloudDesigner status summary"""

    status: str  # running, stopped, not_created, unknown
    port: int | None = None


class LogEntrySummary(BaseModel):
    """Summary of a log entry"""

    timestamp: str
    level: str
    logger: str
    message: str
    execution_id: str | None = None


class SystemSummary(BaseModel):
    """System status summary"""

    browser_available: bool = False
    active_executions: int = 0
    log_stats: dict[str, Any] | None = None


class ContextSummaryResponse(BaseModel):
    """Complete context summary for AI assistant"""

    playbooks: list[PlaybookSummary]
    recent_executions: list[ExecutionSummary]
    credentials: list[CredentialSummary]
    clouddesigner: CloudDesignerSummary
    system: SystemSummary
    recent_logs: list[LogEntrySummary] = []


class FullContextResponse(BaseModel):
    """Full context with all available data for AI assistant"""

    playbooks: list[PlaybookSummary]
    executions: list[ExecutionSummary]
    credentials: list[CredentialSummary]
    clouddesigner: CloudDesignerSummary
    system: SystemSummary
    logs: list[LogEntrySummary]
    error_logs: list[LogEntrySummary]


# ============================================================================
# Routes
# ============================================================================


@router.get("/summary", response_model=ContextSummaryResponse)
async def get_context_summary():
    """
    Get project context summary for AI assistant.

    Returns:
        ContextSummaryResponse with playbooks, executions, credentials, and system info
    """
    try:
        # Get playbooks
        playbooks = await _get_playbooks_summary()

        # Get recent executions
        executions = await _get_executions_summary(limit=10, include_steps=False)

        # Get credential names
        credentials = await _get_credentials_summary()

        # Get CloudDesigner status
        clouddesigner = await _get_clouddesigner_summary()

        # Get system status
        system = await _get_system_summary()

        # Get recent logs (last 20)
        recent_logs = await _get_logs_summary(limit=20)

        return ContextSummaryResponse(
            playbooks=playbooks,
            recent_executions=executions,
            credentials=credentials,
            clouddesigner=clouddesigner,
            system=system,
            recent_logs=recent_logs,
        )
    except Exception as e:
        logger.exception("Error getting context summary")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/full", response_model=FullContextResponse)
async def get_full_context(
    execution_limit: int = Query(default=20, ge=1, le=100, description="Number of executions to include"),
    log_limit: int = Query(default=100, ge=1, le=500, description="Number of logs to include"),
):
    """
    Get full project context for AI assistant with detailed data.

    This endpoint provides comprehensive context including:
    - All playbooks with details
    - Recent executions with step results
    - Credentials (names and gateway URLs, no secrets)
    - CloudDesigner status
    - System status with log statistics
    - Recent logs (all levels)
    - Error logs specifically
    """
    try:
        # Get playbooks
        playbooks = await _get_playbooks_summary()

        # Get executions with step results
        executions = await _get_executions_summary(limit=execution_limit, include_steps=True)

        # Get credentials with gateway URLs
        credentials = await _get_credentials_summary(include_gateway_url=True)

        # Get CloudDesigner status
        clouddesigner = await _get_clouddesigner_summary()

        # Get system status with log stats
        system = await _get_system_summary(include_log_stats=True)

        # Get all recent logs
        logs = await _get_logs_summary(limit=log_limit)

        # Get error logs specifically
        error_logs = await _get_logs_summary(limit=50, level="ERROR")

        return FullContextResponse(
            playbooks=playbooks,
            executions=executions,
            credentials=credentials,
            clouddesigner=clouddesigner,
            system=system,
            logs=logs,
            error_logs=error_logs,
        )
    except Exception as e:
        logger.exception("Error getting full context")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/{execution_id}")
async def get_execution_context(execution_id: str):
    """
    Get detailed context for a specific execution.

    Includes step results, parameters, and related logs.
    """
    try:
        db = get_database()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        with db.session_scope() as session:
            from ignition_toolkit.storage.models import ExecutionModel

            execution = (
                session.query(ExecutionModel)
                .filter(ExecutionModel.execution_id == execution_id)
                .first()
            )

            if not execution:
                raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

            # Build step results
            step_results = []
            for step in execution.step_results:
                duration = None
                if step.started_at and step.completed_at:
                    duration = (step.completed_at - step.started_at).total_seconds()
                step_results.append(
                    StepResultSummary(
                        step_name=step.step_name,
                        status=step.status,
                        error=step.error_message,
                        duration_seconds=duration,
                    )
                )

            # Get execution-specific logs
            logs = await _get_logs_summary(limit=200, execution_id=execution_id)

            return {
                "execution": ExecutionSummary(
                    execution_id=execution.execution_id,
                    playbook_name=execution.playbook_name,
                    status=execution.status,
                    started_at=execution.started_at,
                    completed_at=execution.completed_at,
                    error=execution.error_message,
                    step_results=step_results,
                    parameters=execution.execution_metadata.get("parameters") if execution.execution_metadata else None,
                ),
                "logs": logs,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting execution context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper Functions
# ============================================================================


async def _get_playbooks_summary() -> list[PlaybookSummary]:
    """Get summary of all playbooks"""
    from ignition_toolkit.core.paths import get_playbooks_dir
    from ignition_toolkit.playbook.loader import PlaybookLoader

    playbooks = []
    playbooks_dir = get_playbooks_dir()

    if not playbooks_dir.exists():
        return playbooks

    # Find all YAML files in playbooks directory
    for yaml_file in playbooks_dir.rglob("*.yaml"):
        try:
            playbook = PlaybookLoader.load_from_file(yaml_file)
            relative_path = yaml_file.relative_to(playbooks_dir)

            playbooks.append(
                PlaybookSummary(
                    name=playbook.name,
                    description=playbook.description,
                    domain=playbook.domain,
                    step_count=len(playbook.steps) if playbook.steps else 0,
                    path=str(relative_path),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to load playbook {yaml_file}: {e}")
            continue

    return playbooks


async def _get_executions_summary(limit: int = 10, include_steps: bool = False) -> list[ExecutionSummary]:
    """Get summary of recent executions"""
    db = get_database()
    executions = []

    if not db:
        return executions

    try:
        with db.session_scope() as session:
            from ignition_toolkit.storage.models import ExecutionModel

            db_executions = (
                session.query(ExecutionModel)
                .order_by(ExecutionModel.started_at.desc())
                .limit(limit)
                .all()
            )

            for db_exec in db_executions:
                step_results = []
                if include_steps:
                    for step in db_exec.step_results:
                        duration = None
                        if step.started_at and step.completed_at:
                            duration = (step.completed_at - step.started_at).total_seconds()
                        step_results.append(
                            StepResultSummary(
                                step_name=step.step_name,
                                status=step.status,
                                error=step.error_message,
                                duration_seconds=duration,
                            )
                        )

                executions.append(
                    ExecutionSummary(
                        execution_id=db_exec.execution_id,
                        playbook_name=db_exec.playbook_name,
                        status=db_exec.status,
                        started_at=db_exec.started_at,
                        completed_at=db_exec.completed_at,
                        error=db_exec.error_message,
                        step_results=step_results,
                        parameters=db_exec.execution_metadata.get("parameters") if db_exec.execution_metadata else None,
                    )
                )
    except Exception as e:
        logger.exception(f"Error loading executions summary: {e}")

    return executions


async def _get_credentials_summary(include_gateway_url: bool = False) -> list[CredentialSummary]:
    """Get summary of credentials (names only, optionally with gateway URLs)"""
    credentials = []

    try:
        vault = CredentialVault()
        stored_credentials = vault.list_credentials()

        for cred in stored_credentials:
            credentials.append(
                CredentialSummary(
                    name=cred.name,
                    has_gateway_url=bool(cred.gateway_url),
                    gateway_url=cred.gateway_url if include_gateway_url else None,
                )
            )
    except Exception as e:
        logger.warning(f"Error loading credentials summary: {e}")

    return credentials


async def _get_clouddesigner_summary() -> CloudDesignerSummary:
    """Get CloudDesigner status summary"""
    import asyncio

    try:
        from ignition_toolkit.clouddesigner.manager import get_clouddesigner_manager

        manager = get_clouddesigner_manager()
        status = await asyncio.to_thread(manager.get_container_status)

        return CloudDesignerSummary(
            status=status.status,
            port=status.port,
        )
    except Exception as e:
        logger.warning(f"Error getting CloudDesigner status: {e}")
        return CloudDesignerSummary(status="unknown")


async def _get_system_summary(include_log_stats: bool = False) -> SystemSummary:
    """Get system status summary"""
    try:
        from ignition_toolkit.api.app import active_engines

        log_stats = None
        if include_log_stats:
            capture = get_log_capture()
            if capture:
                log_stats = capture.get_stats()

        return SystemSummary(
            browser_available=True,  # Playwright is always available if backend is running
            active_executions=len(active_engines),
            log_stats=log_stats,
        )
    except Exception as e:
        logger.warning(f"Error getting system summary: {e}")
        return SystemSummary()


async def _get_logs_summary(
    limit: int = 50,
    level: str | None = None,
    execution_id: str | None = None,
) -> list[LogEntrySummary]:
    """Get recent logs"""
    logs = []

    try:
        capture = get_log_capture()
        if not capture:
            return logs

        raw_logs = capture.get_logs(
            limit=limit,
            level=level,
            execution_id=execution_id,
        )

        for log in raw_logs:
            logs.append(
                LogEntrySummary(
                    timestamp=log["timestamp"],
                    level=log["level"],
                    logger=log["logger"],
                    message=log["message"],
                    execution_id=log.get("execution_id"),
                )
            )
    except Exception as e:
        logger.warning(f"Error loading logs summary: {e}")

    return logs

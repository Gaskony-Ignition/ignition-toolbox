"""
Toolbox Assistant Actions API Router

Provides action endpoints for the AI assistant to operate the application.
The assistant can execute playbooks, manage credentials, control executions, and diagnose issues.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ignition_toolkit.credentials import CredentialVault
from ignition_toolkit.storage import get_database
from ignition_toolkit.core.paths import get_playbooks_dir
from ignition_toolkit.playbook.loader import PlaybookLoader
from ignition_toolkit.api.services.log_capture import get_log_capture

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ActionRequest(BaseModel):
    """Generic action request"""
    action: str = Field(..., description="The action to perform")
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters")


class ActionResponse(BaseModel):
    """Generic action response"""
    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: str | None = None


class ExecutePlaybookRequest(BaseModel):
    """Request to execute a playbook"""
    playbook_path: str = Field(..., description="Path to the playbook (relative to playbooks directory)")
    credential_name: str | None = Field(None, description="Name of credential to use")
    gateway_url: str | None = Field(None, description="Gateway URL (overrides credential)")
    parameters: dict[str, str] = Field(default_factory=dict, description="Parameter overrides")
    debug_mode: bool = Field(False, description="Enable debug mode (pause after each step)")
    headless: bool = Field(True, description="Run browser in headless mode")


class CapabilitiesResponse(BaseModel):
    """List of Toolbox Assistant capabilities"""
    actions: list[dict[str, Any]]
    examples: list[dict[str, str]]


# ============================================================================
# Capabilities Endpoint
# ============================================================================


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """
    Get list of all actions the Toolbox Assistant can perform.

    This endpoint returns a comprehensive list of capabilities
    that can be referenced in the system prompt.
    """
    actions = [
        {
            "name": "list_playbooks",
            "description": "List all available playbooks with their details",
            "parameters": {
                "domain": "Optional filter by domain (gateway, perspective, designer)"
            }
        },
        {
            "name": "get_playbook_details",
            "description": "Get detailed information about a specific playbook including all steps",
            "parameters": {
                "playbook_path": "Required - path to the playbook"
            }
        },
        {
            "name": "execute_playbook",
            "description": "Execute a playbook with specified parameters",
            "parameters": {
                "playbook_path": "Required - path to the playbook",
                "credential_name": "Optional - credential to use for authentication",
                "gateway_url": "Optional - gateway URL (overrides credential)",
                "parameters": "Optional - dict of parameter overrides",
                "debug_mode": "Optional - pause after each step (default: false)",
                "headless": "Optional - run headless (default: true)"
            }
        },
        {
            "name": "list_executions",
            "description": "List recent playbook executions",
            "parameters": {
                "limit": "Optional - number of executions (default: 20)",
                "status": "Optional - filter by status (running, completed, failed, cancelled)"
            }
        },
        {
            "name": "get_execution_details",
            "description": "Get detailed information about a specific execution",
            "parameters": {
                "execution_id": "Required - the execution ID"
            }
        },
        {
            "name": "control_execution",
            "description": "Control a running execution (pause, resume, skip, cancel)",
            "parameters": {
                "execution_id": "Required - the execution ID",
                "action": "Required - one of: pause, resume, skip, cancel"
            }
        },
        {
            "name": "list_credentials",
            "description": "List all saved credentials (names only, no secrets)",
            "parameters": {}
        },
        {
            "name": "diagnose_execution",
            "description": "Analyze a failed execution and provide diagnostic information",
            "parameters": {
                "execution_id": "Required - the execution ID"
            }
        },
        {
            "name": "get_system_status",
            "description": "Get current system status including active executions and health",
            "parameters": {}
        },
        {
            "name": "get_recent_errors",
            "description": "Get recent error logs for troubleshooting",
            "parameters": {
                "limit": "Optional - number of errors (default: 20)"
            }
        },
        {
            "name": "search_logs",
            "description": "Search logs by keyword or execution ID",
            "parameters": {
                "keyword": "Optional - search term",
                "execution_id": "Optional - filter by execution",
                "level": "Optional - log level (DEBUG, INFO, WARNING, ERROR)",
                "limit": "Optional - number of results (default: 50)"
            }
        }
    ]

    examples = [
        {
            "request": "What gateway playbooks are available?",
            "action": "list_playbooks",
            "params": {"domain": "gateway"}
        },
        {
            "request": "Run the Gateway Login playbook",
            "action": "execute_playbook",
            "params": {"playbook_path": "gateway/login.yaml", "credential_name": "default"}
        },
        {
            "request": "Why did my last execution fail?",
            "action": "diagnose_execution",
            "params": {"execution_id": "<most_recent_failed_execution_id>"}
        },
        {
            "request": "Show me recent errors",
            "action": "get_recent_errors",
            "params": {"limit": 10}
        },
        {
            "request": "Pause the current execution",
            "action": "control_execution",
            "params": {"execution_id": "<current_execution_id>", "action": "pause"}
        }
    ]

    return CapabilitiesResponse(actions=actions, examples=examples)


# ============================================================================
# Action Execution Endpoint
# ============================================================================


@router.post("/execute", response_model=ActionResponse)
async def execute_action(request: ActionRequest):
    """
    Execute a Toolbox Assistant action.

    This is the main endpoint for the assistant to perform operations.
    """
    action = request.action.lower().replace("-", "_").replace(" ", "_")
    params = request.params

    try:
        if action == "list_playbooks":
            return await _action_list_playbooks(params)
        elif action == "get_playbook_details":
            return await _action_get_playbook_details(params)
        elif action == "execute_playbook":
            return await _action_execute_playbook(params)
        elif action == "list_executions":
            return await _action_list_executions(params)
        elif action == "get_execution_details":
            return await _action_get_execution_details(params)
        elif action == "control_execution":
            return await _action_control_execution(params)
        elif action == "list_credentials":
            return await _action_list_credentials(params)
        elif action == "diagnose_execution":
            return await _action_diagnose_execution(params)
        elif action == "get_system_status":
            return await _action_get_system_status(params)
        elif action == "get_recent_errors":
            return await _action_get_recent_errors(params)
        elif action == "search_logs":
            return await _action_search_logs(params)
        else:
            return ActionResponse(
                success=False,
                message=f"Unknown action: {action}",
                error=f"Available actions: list_playbooks, get_playbook_details, execute_playbook, list_executions, get_execution_details, control_execution, list_credentials, diagnose_execution, get_system_status, get_recent_errors, search_logs"
            )
    except Exception as e:
        logger.exception(f"Error executing action {action}: {e}")
        return ActionResponse(
            success=False,
            message=f"Action failed: {str(e)}",
            error=str(e)
        )


# ============================================================================
# Action Implementations
# ============================================================================


async def _action_list_playbooks(params: dict) -> ActionResponse:
    """List all playbooks, optionally filtered by domain"""
    domain_filter = params.get("domain")
    playbooks_dir = get_playbooks_dir()

    if not playbooks_dir.exists():
        return ActionResponse(
            success=True,
            message="No playbooks directory found",
            data={"playbooks": [], "count": 0}
        )

    playbooks = []
    for yaml_file in playbooks_dir.rglob("*.yaml"):
        try:
            playbook = PlaybookLoader.load_from_file(yaml_file)

            # Apply domain filter
            if domain_filter and playbook.domain != domain_filter:
                continue

            relative_path = yaml_file.relative_to(playbooks_dir)
            playbooks.append({
                "name": playbook.name,
                "description": playbook.description,
                "domain": playbook.domain,
                "path": str(relative_path),
                "step_count": len(playbook.steps) if playbook.steps else 0,
                "parameters": [
                    {"name": p.name, "required": p.required, "description": p.description}
                    for p in (playbook.parameters or [])
                ],
                "version": playbook.version,
                "enabled": playbook.enabled,
                "verified": playbook.verified,
            })
        except Exception as e:
            logger.warning(f"Failed to load playbook {yaml_file}: {e}")

    # Sort by domain then name
    playbooks.sort(key=lambda p: (p.get("domain") or "", p.get("name") or ""))

    domain_msg = f" for domain '{domain_filter}'" if domain_filter else ""
    return ActionResponse(
        success=True,
        message=f"Found {len(playbooks)} playbooks{domain_msg}",
        data={"playbooks": playbooks, "count": len(playbooks)}
    )


async def _action_get_playbook_details(params: dict) -> ActionResponse:
    """Get detailed information about a specific playbook"""
    playbook_path = params.get("playbook_path")
    if not playbook_path:
        return ActionResponse(
            success=False,
            message="playbook_path is required",
            error="Missing required parameter: playbook_path"
        )

    playbooks_dir = get_playbooks_dir()
    full_path = playbooks_dir / playbook_path

    if not full_path.exists():
        # Try to find it with .yaml extension
        if not playbook_path.endswith(".yaml"):
            full_path = playbooks_dir / f"{playbook_path}.yaml"

    if not full_path.exists():
        return ActionResponse(
            success=False,
            message=f"Playbook not found: {playbook_path}",
            error="Playbook file does not exist"
        )

    try:
        playbook = PlaybookLoader.load_from_file(full_path)

        steps = []
        for i, step in enumerate(playbook.steps or []):
            steps.append({
                "index": i,
                "id": step.id,
                "name": step.name,
                "type": step.type,
                "description": getattr(step, "description", None),
            })

        return ActionResponse(
            success=True,
            message=f"Playbook details for '{playbook.name}'",
            data={
                "name": playbook.name,
                "description": playbook.description,
                "domain": playbook.domain,
                "version": playbook.version,
                "path": playbook_path,
                "enabled": playbook.enabled,
                "verified": playbook.verified,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "required": p.required,
                        "default": p.default,
                        "description": p.description,
                    }
                    for p in (playbook.parameters or [])
                ],
                "steps": steps,
                "step_count": len(steps),
            }
        )
    except Exception as e:
        return ActionResponse(
            success=False,
            message=f"Failed to load playbook: {e}",
            error=str(e)
        )


async def _action_execute_playbook(params: dict) -> ActionResponse:
    """Execute a playbook"""
    playbook_path = params.get("playbook_path")
    if not playbook_path:
        return ActionResponse(
            success=False,
            message="playbook_path is required",
            error="Missing required parameter: playbook_path"
        )

    # Import here to avoid circular imports
    from ignition_toolkit.api.app import active_engines
    from ignition_toolkit.playbook.engine import PlaybookEngine

    playbooks_dir = get_playbooks_dir()
    full_path = playbooks_dir / playbook_path

    if not full_path.exists():
        if not playbook_path.endswith(".yaml"):
            full_path = playbooks_dir / f"{playbook_path}.yaml"

    if not full_path.exists():
        return ActionResponse(
            success=False,
            message=f"Playbook not found: {playbook_path}",
            error="Playbook file does not exist"
        )

    # Get credential if specified
    credential_name = params.get("credential_name")
    gateway_url = params.get("gateway_url")
    credential = None

    if credential_name:
        try:
            vault = CredentialVault()
            credential = vault.get_credential(credential_name)
            if not gateway_url and credential:
                gateway_url = credential.gateway_url
        except Exception as e:
            logger.warning(f"Could not load credential {credential_name}: {e}")

    # Create execution
    execution_id = str(uuid.uuid4())
    parameters = params.get("parameters", {})
    debug_mode = params.get("debug_mode", False)
    headless = params.get("headless", True)

    try:
        # Create and start engine
        engine = PlaybookEngine(
            playbook_path=str(full_path),
            gateway_url=gateway_url,
            credential=credential,
            parameters=parameters,
            headless=headless,
            execution_id=execution_id,
        )

        if debug_mode:
            engine.enable_debug_mode()

        # Store engine reference
        active_engines[execution_id] = engine

        # Start execution in background
        import asyncio

        async def run_execution():
            try:
                await engine.run()
            finally:
                if execution_id in active_engines:
                    del active_engines[execution_id]

        asyncio.create_task(run_execution())

        return ActionResponse(
            success=True,
            message=f"Started execution of '{playbook_path}'",
            data={
                "execution_id": execution_id,
                "playbook_path": playbook_path,
                "gateway_url": gateway_url,
                "debug_mode": debug_mode,
                "headless": headless,
            }
        )
    except Exception as e:
        return ActionResponse(
            success=False,
            message=f"Failed to start execution: {e}",
            error=str(e)
        )


async def _action_list_executions(params: dict) -> ActionResponse:
    """List recent executions"""
    limit = params.get("limit", 20)
    status_filter = params.get("status")

    db = get_database()
    if not db:
        return ActionResponse(
            success=False,
            message="Database not available",
            error="Database connection failed"
        )

    try:
        with db.session_scope() as session:
            from ignition_toolkit.storage.models import ExecutionModel

            query = session.query(ExecutionModel)

            if status_filter:
                query = query.filter(ExecutionModel.status == status_filter)

            executions = (
                query.order_by(ExecutionModel.started_at.desc())
                .limit(limit)
                .all()
            )

            exec_list = []
            for ex in executions:
                exec_list.append({
                    "execution_id": ex.execution_id,
                    "playbook_name": ex.playbook_name,
                    "status": ex.status,
                    "started_at": ex.started_at.isoformat() if ex.started_at else None,
                    "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                    "error": ex.error_message,
                    "step_count": len(ex.step_results),
                    "failed_steps": sum(1 for s in ex.step_results if s.status == "failed"),
                })

            return ActionResponse(
                success=True,
                message=f"Found {len(exec_list)} executions",
                data={"executions": exec_list, "count": len(exec_list)}
            )
    except Exception as e:
        return ActionResponse(
            success=False,
            message=f"Failed to list executions: {e}",
            error=str(e)
        )


async def _action_get_execution_details(params: dict) -> ActionResponse:
    """Get detailed information about an execution"""
    execution_id = params.get("execution_id")
    if not execution_id:
        return ActionResponse(
            success=False,
            message="execution_id is required",
            error="Missing required parameter: execution_id"
        )

    db = get_database()
    if not db:
        return ActionResponse(
            success=False,
            message="Database not available",
            error="Database connection failed"
        )

    try:
        with db.session_scope() as session:
            from ignition_toolkit.storage.models import ExecutionModel

            execution = (
                session.query(ExecutionModel)
                .filter(ExecutionModel.execution_id == execution_id)
                .first()
            )

            if not execution:
                return ActionResponse(
                    success=False,
                    message=f"Execution not found: {execution_id}",
                    error="Execution does not exist"
                )

            steps = []
            for step in execution.step_results:
                duration = None
                if step.started_at and step.completed_at:
                    duration = (step.completed_at - step.started_at).total_seconds()
                steps.append({
                    "step_id": step.step_id,
                    "step_name": step.step_name,
                    "status": step.status,
                    "error": step.error_message,
                    "duration_seconds": duration,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                })

            return ActionResponse(
                success=True,
                message=f"Execution details for {execution_id}",
                data={
                    "execution_id": execution.execution_id,
                    "playbook_name": execution.playbook_name,
                    "playbook_path": execution.playbook_path,
                    "status": execution.status,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "error": execution.error_message,
                    "parameters": execution.execution_metadata.get("parameters") if execution.execution_metadata else None,
                    "steps": steps,
                    "step_count": len(steps),
                    "completed_steps": sum(1 for s in steps if s["status"] == "completed"),
                    "failed_steps": sum(1 for s in steps if s["status"] == "failed"),
                }
            )
    except Exception as e:
        return ActionResponse(
            success=False,
            message=f"Failed to get execution details: {e}",
            error=str(e)
        )


async def _action_control_execution(params: dict) -> ActionResponse:
    """Control a running execution"""
    execution_id = params.get("execution_id")
    action = params.get("action")

    if not execution_id:
        return ActionResponse(
            success=False,
            message="execution_id is required",
            error="Missing required parameter: execution_id"
        )

    if not action:
        return ActionResponse(
            success=False,
            message="action is required (pause, resume, skip, cancel)",
            error="Missing required parameter: action"
        )

    from ignition_toolkit.api.app import active_engines

    engine = active_engines.get(execution_id)
    if not engine:
        return ActionResponse(
            success=False,
            message=f"Execution {execution_id} is not currently running",
            error="Execution not found in active engines"
        )

    action = action.lower()
    try:
        if action == "pause":
            engine.pause()
            return ActionResponse(
                success=True,
                message=f"Paused execution {execution_id}",
                data={"execution_id": execution_id, "action": "pause"}
            )
        elif action == "resume":
            engine.resume()
            return ActionResponse(
                success=True,
                message=f"Resumed execution {execution_id}",
                data={"execution_id": execution_id, "action": "resume"}
            )
        elif action == "skip":
            engine.skip_step()
            return ActionResponse(
                success=True,
                message=f"Skipped current step in execution {execution_id}",
                data={"execution_id": execution_id, "action": "skip"}
            )
        elif action == "cancel":
            engine.cancel()
            return ActionResponse(
                success=True,
                message=f"Cancelled execution {execution_id}",
                data={"execution_id": execution_id, "action": "cancel"}
            )
        else:
            return ActionResponse(
                success=False,
                message=f"Unknown action: {action}",
                error="Valid actions: pause, resume, skip, cancel"
            )
    except Exception as e:
        return ActionResponse(
            success=False,
            message=f"Failed to {action} execution: {e}",
            error=str(e)
        )


async def _action_list_credentials(params: dict) -> ActionResponse:
    """List all credentials (names and gateway URLs only)"""
    try:
        vault = CredentialVault()
        credentials = vault.list_credentials()

        cred_list = []
        for cred in credentials:
            cred_list.append({
                "name": cred.name,
                "username": cred.username,
                "gateway_url": cred.gateway_url,
                "description": cred.description,
            })

        return ActionResponse(
            success=True,
            message=f"Found {len(cred_list)} credentials",
            data={"credentials": cred_list, "count": len(cred_list)}
        )
    except Exception as e:
        return ActionResponse(
            success=False,
            message=f"Failed to list credentials: {e}",
            error=str(e)
        )


async def _action_diagnose_execution(params: dict) -> ActionResponse:
    """Diagnose a failed execution"""
    execution_id = params.get("execution_id")
    if not execution_id:
        # If no execution_id, get the most recent failed execution
        db = get_database()
        if db:
            with db.session_scope() as session:
                from ignition_toolkit.storage.models import ExecutionModel

                failed = (
                    session.query(ExecutionModel)
                    .filter(ExecutionModel.status == "failed")
                    .order_by(ExecutionModel.started_at.desc())
                    .first()
                )
                if failed:
                    execution_id = failed.execution_id

    if not execution_id:
        return ActionResponse(
            success=False,
            message="No execution_id provided and no failed executions found",
            error="Provide an execution_id or run a playbook first"
        )

    # Get execution details
    exec_result = await _action_get_execution_details({"execution_id": execution_id})
    if not exec_result.success:
        return exec_result

    execution = exec_result.data

    # Get execution-specific logs
    capture = get_log_capture()
    error_logs = []
    if capture:
        logs = capture.get_logs(limit=100, execution_id=execution_id)
        error_logs = [l for l in logs if l.get("level") in ("ERROR", "WARNING")]

    # Build diagnosis
    diagnosis = {
        "execution_id": execution_id,
        "playbook_name": execution.get("playbook_name"),
        "status": execution.get("status"),
        "error": execution.get("error"),
        "duration_seconds": None,
        "failed_step": None,
        "error_logs": error_logs[:20],
        "suggestions": [],
    }

    # Calculate duration
    if execution.get("started_at") and execution.get("completed_at"):
        started = datetime.fromisoformat(execution["started_at"])
        completed = datetime.fromisoformat(execution["completed_at"])
        diagnosis["duration_seconds"] = (completed - started).total_seconds()

    # Find failed step
    for step in execution.get("steps", []):
        if step.get("status") == "failed":
            diagnosis["failed_step"] = {
                "name": step.get("step_name"),
                "error": step.get("error"),
                "step_id": step.get("step_id"),
            }
            break

    # Generate suggestions based on error patterns
    error_msg = (execution.get("error") or "").lower()
    step_error = (diagnosis.get("failed_step", {}) or {}).get("error", "").lower() if diagnosis.get("failed_step") else ""

    if "timeout" in error_msg or "timeout" in step_error:
        diagnosis["suggestions"].append("Increase timeout settings in playbook execution parameters")
        diagnosis["suggestions"].append("Check if the target system is responding slowly")

    if "authentication" in error_msg or "401" in error_msg or "login" in step_error:
        diagnosis["suggestions"].append("Verify the credential username and password are correct")
        diagnosis["suggestions"].append("Check if the account is locked or expired")

    if "connection" in error_msg or "refused" in error_msg:
        diagnosis["suggestions"].append("Verify the gateway URL is correct and accessible")
        diagnosis["suggestions"].append("Check network connectivity and firewall settings")

    if "not found" in error_msg or "404" in error_msg:
        diagnosis["suggestions"].append("Verify the resource exists on the gateway")
        diagnosis["suggestions"].append("Check for typos in project names or resource paths")

    if "element" in step_error and ("not found" in step_error or "visible" in step_error):
        diagnosis["suggestions"].append("The page may have changed - verify selectors are still valid")
        diagnosis["suggestions"].append("Add explicit wait steps before interacting with elements")

    if not diagnosis["suggestions"]:
        diagnosis["suggestions"].append("Review the error logs for more details")
        diagnosis["suggestions"].append("Try running with debug_mode=true to step through execution")

    return ActionResponse(
        success=True,
        message=f"Diagnosis for execution {execution_id}",
        data=diagnosis
    )


async def _action_get_system_status(params: dict) -> ActionResponse:
    """Get current system status"""
    from ignition_toolkit.api.app import active_engines

    # Get active executions
    active = []
    for exec_id, engine in active_engines.items():
        active.append({
            "execution_id": exec_id,
            "playbook_name": engine.playbook_name if hasattr(engine, "playbook_name") else "unknown",
            "status": engine.status if hasattr(engine, "status") else "running",
        })

    # Get database stats
    db = get_database()
    db_stats = {"available": False}
    if db:
        try:
            with db.session_scope() as session:
                from ignition_toolkit.storage.models import ExecutionModel

                total = session.query(ExecutionModel).count()
                running = session.query(ExecutionModel).filter(ExecutionModel.status == "running").count()
                failed = session.query(ExecutionModel).filter(ExecutionModel.status == "failed").count()

                db_stats = {
                    "available": True,
                    "total_executions": total,
                    "running": running,
                    "failed": failed,
                }
        except Exception as e:
            db_stats["error"] = str(e)

    # Get log stats
    log_stats = {}
    capture = get_log_capture()
    if capture:
        log_stats = capture.get_stats()

    return ActionResponse(
        success=True,
        message="System status",
        data={
            "active_executions": active,
            "active_count": len(active),
            "database": db_stats,
            "logs": log_stats,
        }
    )


async def _action_get_recent_errors(params: dict) -> ActionResponse:
    """Get recent error logs"""
    limit = params.get("limit", 20)

    capture = get_log_capture()
    if not capture:
        return ActionResponse(
            success=False,
            message="Log capture not available",
            error="Log capture system not initialized"
        )

    logs = capture.get_logs(limit=limit, level="ERROR")

    return ActionResponse(
        success=True,
        message=f"Found {len(logs)} error logs",
        data={"errors": logs, "count": len(logs)}
    )


async def _action_search_logs(params: dict) -> ActionResponse:
    """Search logs by keyword or filters"""
    keyword = params.get("keyword")
    execution_id = params.get("execution_id")
    level = params.get("level")
    limit = params.get("limit", 50)

    capture = get_log_capture()
    if not capture:
        return ActionResponse(
            success=False,
            message="Log capture not available",
            error="Log capture system not initialized"
        )

    logs = capture.get_logs(
        limit=limit,
        level=level,
        execution_id=execution_id,
    )

    # Apply keyword filter if specified
    if keyword:
        keyword_lower = keyword.lower()
        logs = [l for l in logs if keyword_lower in l.get("message", "").lower()]

    return ActionResponse(
        success=True,
        message=f"Found {len(logs)} logs",
        data={"logs": logs, "count": len(logs)}
    )

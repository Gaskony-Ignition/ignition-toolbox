"""
Execution Queue API Router

Provides endpoints for:
- Queue management (enqueue, cancel, status)
- Parallel execution
- Resource monitoring
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ignition_toolkit.execution import (
    ExecutionQueue,
    ExecutionPriority,
    ParallelExecutionManager,
    ResourceLimiter,
    ResourceType,
    get_execution_queue,
    get_parallel_manager,
    get_resource_limiter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/execution-queue", tags=["Execution Queue"])


# Request/Response Models

class EnqueueRequest(BaseModel):
    """Request to enqueue a playbook execution"""
    playbook_path: str = Field(..., description="Path to playbook YAML file")
    parameters: dict[str, Any] | None = Field(default=None, description="Playbook parameters")
    gateway_url: str | None = Field(default=None, description="Gateway URL")
    credential_name: str | None = Field(default=None, description="Credential name")
    priority: str = Field(default="normal", description="Priority: high, normal, low")


class ParallelExecutionRequest(BaseModel):
    """Request to run playbooks in parallel"""
    playbooks: list[dict[str, Any]] = Field(..., description="List of playbook configurations")
    fail_fast: bool = Field(default=False, description="Cancel remaining on first failure")


class ResourceLimitUpdate(BaseModel):
    """Request to update resource limits"""
    browser_limit: int | None = Field(default=None, ge=1, le=20)
    gateway_limit: int | None = Field(default=None, ge=1, le=50)
    memory_limit: int | None = Field(default=None, ge=1, le=20)
    cpu_limit: int | None = Field(default=None, ge=1, le=16)


class QueueSettingsUpdate(BaseModel):
    """Request to update queue settings"""
    max_concurrent: int = Field(..., ge=1, le=20, description="Maximum concurrent executions")


# Endpoints

@router.get("/status")
async def get_queue_status():
    """
    Get execution queue status

    Returns current queue statistics including:
    - Queued count
    - Running count
    - Available slots
    - Recent completed executions
    """
    queue = get_execution_queue()
    return queue.get_status()


@router.post("/enqueue")
async def enqueue_execution(request: EnqueueRequest):
    """
    Add a playbook execution to the queue

    The execution will be processed based on priority and available slots.
    """
    # Convert priority string to enum
    priority_map = {
        "high": ExecutionPriority.HIGH,
        "normal": ExecutionPriority.NORMAL,
        "low": ExecutionPriority.LOW,
    }
    priority = priority_map.get(request.priority.lower(), ExecutionPriority.NORMAL)

    queue = get_execution_queue()
    execution = await queue.enqueue(
        playbook_path=request.playbook_path,
        parameters=request.parameters,
        gateway_url=request.gateway_url,
        credential_name=request.credential_name,
        priority=priority,
    )

    return {
        "success": True,
        "message": f"Execution queued with priority {priority.name}",
        "execution": execution.to_dict(),
    }


@router.delete("/cancel/{execution_id}")
async def cancel_queued_execution(execution_id: str):
    """
    Cancel a queued execution

    Only queued (not yet running) executions can be cancelled.
    """
    queue = get_execution_queue()
    cancelled = await queue.cancel(execution_id)

    if cancelled:
        return {"success": True, "message": "Execution cancelled"}
    else:
        raise HTTPException(
            status_code=404,
            detail="Execution not found or already running"
        )


@router.get("/running")
async def get_running_executions():
    """
    Get list of currently running executions
    """
    queue = get_execution_queue()
    return {
        "running": [e.to_dict() for e in queue.get_running()],
        "count": len(queue.get_running()),
    }


# Parallel Execution Endpoints

@router.post("/parallel")
async def run_parallel_executions(request: ParallelExecutionRequest):
    """
    Run multiple playbooks in parallel

    Executes all provided playbooks concurrently, respecting resource limits.
    """
    if not request.playbooks:
        raise HTTPException(status_code=400, detail="No playbooks provided")

    if len(request.playbooks) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 playbooks per parallel execution")

    manager = get_parallel_manager()

    # Define execution function (this would integrate with the actual playbook engine)
    async def execute_playbook(config: dict) -> dict:
        # This is a placeholder - in real implementation, this would call the playbook engine
        # For now, return a mock result
        return {
            "execution_id": f"exec_{config.get('playbook_path', 'unknown')}",
            "status": "completed",
        }

    results = await manager.run_parallel(
        playbook_configs=request.playbooks,
        execution_fn=execute_playbook,
        fail_fast=request.fail_fast,
    )

    return results


@router.get("/parallel/status")
async def get_parallel_execution_status():
    """
    Get parallel execution manager status
    """
    manager = get_parallel_manager()
    return manager.get_status()


@router.delete("/parallel/cancel/{execution_id}")
async def cancel_parallel_execution(execution_id: str):
    """
    Cancel a running parallel execution
    """
    manager = get_parallel_manager()
    cancelled = await manager.cancel(execution_id)

    if cancelled:
        return {"success": True, "message": "Execution cancelled"}
    else:
        raise HTTPException(
            status_code=404,
            detail="Execution not found or already completed"
        )


# Resource Management Endpoints

@router.get("/resources")
async def get_resource_status():
    """
    Get resource limiter status

    Shows availability of shared resources:
    - Browser instances
    - Gateway connections
    - Memory slots
    - CPU slots
    """
    limiter = get_resource_limiter()
    return limiter.get_status()


@router.put("/resources/limits")
async def update_resource_limits(request: ResourceLimitUpdate):
    """
    Update resource limits

    Allows adjusting limits for different resource types.
    """
    limiter = get_resource_limiter()

    if request.browser_limit:
        limiter.set_limit(ResourceType.BROWSER, request.browser_limit)

    if request.gateway_limit:
        limiter.set_limit(ResourceType.GATEWAY, request.gateway_limit)

    if request.memory_limit:
        limiter.set_limit(ResourceType.MEMORY, request.memory_limit)

    if request.cpu_limit:
        limiter.set_limit(ResourceType.CPU, request.cpu_limit)

    return {
        "success": True,
        "message": "Resource limits updated",
        "status": limiter.get_status(),
    }


# Import functions for module-level access
from ignition_toolkit.execution.queue import get_execution_queue
from ignition_toolkit.execution.parallel import get_parallel_manager
from ignition_toolkit.execution.resource_limiter import get_resource_limiter

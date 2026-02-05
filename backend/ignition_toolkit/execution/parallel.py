"""
Parallel Execution Manager

Manages concurrent playbook executions with resource limiting and monitoring.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import uuid4

from ignition_toolkit.execution.resource_limiter import ResourceLimiter, ResourceType

logger = logging.getLogger(__name__)


@dataclass
class ParallelExecution:
    """Tracks a parallel execution"""
    id: str = field(default_factory=lambda: str(uuid4()))
    playbook_path: str = ""
    execution_id: str | None = None
    task: asyncio.Task | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: str = "running"  # running, completed, failed, cancelled
    error: str | None = None
    result: Any = None


class ParallelExecutionManager:
    """
    Manages parallel playbook executions

    Features:
    - Run multiple playbooks concurrently
    - Resource limiting (browsers, gateways, memory)
    - Execution monitoring and cancellation
    - Result aggregation

    Example:
        manager = ParallelExecutionManager(max_parallel=5)

        # Run playbooks in parallel
        results = await manager.run_parallel([
            {"playbook_path": "playbook1.yaml"},
            {"playbook_path": "playbook2.yaml"},
            {"playbook_path": "playbook3.yaml"},
        ])
    """

    def __init__(
        self,
        max_parallel: int = 5,
        resource_limiter: ResourceLimiter | None = None,
    ):
        """
        Initialize parallel execution manager

        Args:
            max_parallel: Maximum parallel executions
            resource_limiter: Optional resource limiter instance
        """
        self.max_parallel = max_parallel
        self.resource_limiter = resource_limiter or ResourceLimiter()
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._executions: dict[str, ParallelExecution] = {}
        self._lock = asyncio.Lock()

        logger.info(f"ParallelExecutionManager initialized with max_parallel={max_parallel}")

    async def run_parallel(
        self,
        playbook_configs: list[dict[str, Any]],
        execution_fn: Callable,
        fail_fast: bool = False,
    ) -> dict[str, Any]:
        """
        Run multiple playbooks in parallel

        Args:
            playbook_configs: List of playbook configurations
            execution_fn: Async function to execute each playbook
            fail_fast: If True, cancel remaining on first failure

        Returns:
            Dictionary with results for each playbook
        """
        if not playbook_configs:
            return {"results": [], "summary": {"total": 0, "completed": 0, "failed": 0}}

        logger.info(f"Starting parallel execution of {len(playbook_configs)} playbooks")

        # Create execution tasks
        tasks: list[asyncio.Task] = []
        executions: list[ParallelExecution] = []

        for config in playbook_configs:
            execution = ParallelExecution(
                playbook_path=config.get("playbook_path", "unknown"),
            )
            executions.append(execution)

            task = asyncio.create_task(
                self._run_single(execution, config, execution_fn)
            )
            execution.task = task
            tasks.append(task)

            async with self._lock:
                self._executions[execution.id] = execution

        # Wait for all to complete (or fail fast)
        if fail_fast:
            results = await self._wait_fail_fast(tasks, executions)
        else:
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result summary
        completed = sum(1 for e in executions if e.status == "completed")
        failed = sum(1 for e in executions if e.status == "failed")
        cancelled = sum(1 for e in executions if e.status == "cancelled")

        logger.info(f"Parallel execution complete: {completed} succeeded, {failed} failed, {cancelled} cancelled")

        return {
            "results": [
                {
                    "id": e.id,
                    "playbook_path": e.playbook_path,
                    "execution_id": e.execution_id,
                    "status": e.status,
                    "error": e.error,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                }
                for e in executions
            ],
            "summary": {
                "total": len(executions),
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
            },
        }

    async def _run_single(
        self,
        execution: ParallelExecution,
        config: dict[str, Any],
        execution_fn: Callable,
    ) -> Any:
        """Run a single playbook with resource limiting"""
        async with self._semaphore:
            # Acquire resources
            resources_acquired = []
            try:
                # Check what resources this playbook needs
                playbook_path = config.get("playbook_path", "")

                # Browser-based playbooks need browser resource
                if any(domain in playbook_path.lower() for domain in ["perspective", "browser", "designer"]):
                    await self.resource_limiter.acquire(ResourceType.BROWSER)
                    resources_acquired.append(ResourceType.BROWSER)

                # Gateway-based playbooks need gateway resource
                if "gateway" in config or config.get("gateway_url"):
                    await self.resource_limiter.acquire(ResourceType.GATEWAY)
                    resources_acquired.append(ResourceType.GATEWAY)

                # Execute
                logger.info(f"Executing {execution.playbook_path}")
                result = await execution_fn(config)

                execution.result = result
                execution.execution_id = result.get("execution_id") if isinstance(result, dict) else None
                execution.status = "completed"
                execution.completed_at = datetime.now(UTC)

                return result

            except asyncio.CancelledError:
                execution.status = "cancelled"
                execution.completed_at = datetime.now(UTC)
                raise

            except Exception as e:
                execution.status = "failed"
                execution.error = str(e)
                execution.completed_at = datetime.now(UTC)
                logger.error(f"Execution {execution.id} failed: {e}")
                raise

            finally:
                # Release resources
                for resource in resources_acquired:
                    self.resource_limiter.release(resource)

    async def _wait_fail_fast(
        self,
        tasks: list[asyncio.Task],
        executions: list[ParallelExecution],
    ) -> list[Any]:
        """Wait for tasks with fail-fast behavior"""
        results = []
        pending = set(tasks)

        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                try:
                    result = task.result()
                    results.append(result)
                except Exception as e:
                    # Cancel remaining tasks
                    for p in pending:
                        p.cancel()

                    # Mark cancelled executions
                    for execution in executions:
                        if execution.task in pending:
                            execution.status = "cancelled"
                            execution.completed_at = datetime.now(UTC)

                    raise e

        return results

    async def cancel(self, execution_id: str) -> bool:
        """
        Cancel a running parallel execution

        Args:
            execution_id: ID of execution to cancel

        Returns:
            True if cancelled, False if not found
        """
        async with self._lock:
            if execution_id not in self._executions:
                return False

            execution = self._executions[execution_id]
            if execution.task and not execution.task.done():
                execution.task.cancel()
                execution.status = "cancelled"
                execution.completed_at = datetime.now(UTC)
                logger.info(f"Cancelled execution {execution_id}")
                return True

            return False

    def get_running(self) -> list[dict]:
        """Get list of running executions"""
        return [
            {
                "id": e.id,
                "playbook_path": e.playbook_path,
                "status": e.status,
                "started_at": e.started_at.isoformat() if e.started_at else None,
            }
            for e in self._executions.values()
            if e.status == "running"
        ]

    def get_status(self) -> dict:
        """Get manager status"""
        running = sum(1 for e in self._executions.values() if e.status == "running")
        return {
            "max_parallel": self.max_parallel,
            "running_count": running,
            "available_slots": max(0, self.max_parallel - running),
            "resource_status": self.resource_limiter.get_status(),
        }


# Global instance
_parallel_manager: ParallelExecutionManager | None = None


def get_parallel_manager() -> ParallelExecutionManager:
    """Get the global parallel execution manager"""
    global _parallel_manager
    if _parallel_manager is None:
        _parallel_manager = ParallelExecutionManager()
    return _parallel_manager

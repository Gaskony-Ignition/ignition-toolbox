"""
Execution Queue - Manages queued playbook executions

Provides a priority queue for scheduling playbook executions with:
- Priority levels (high, normal, low)
- FIFO ordering within priority levels
- Concurrency limits
- Queue status monitoring
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExecutionPriority(Enum):
    """Execution priority levels"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


class ExecutionState(Enum):
    """States for queued executions"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedExecution:
    """Represents a queued playbook execution"""
    id: str = field(default_factory=lambda: str(uuid4()))
    playbook_path: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    gateway_url: str | None = None
    credential_name: str | None = None
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    state: ExecutionState = ExecutionState.QUEUED
    queued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_id: str | None = None  # Links to actual execution once started
    error_message: str | None = None

    def __lt__(self, other: "QueuedExecution") -> bool:
        """Compare by priority then by queue time (FIFO within priority)"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.queued_at < other.queued_at

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "playbook_path": self.playbook_path,
            "parameters": self.parameters,
            "gateway_url": self.gateway_url,
            "credential_name": self.credential_name,
            "priority": self.priority.value,
            "priority_name": self.priority.name,
            "state": self.state.value,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_id": self.execution_id,
            "error_message": self.error_message,
        }


class ExecutionQueue:
    """
    Priority queue for playbook executions

    Features:
    - Priority-based scheduling (high, normal, low)
    - Configurable concurrency limit
    - Automatic execution when slots available
    - Queue status monitoring

    Example:
        queue = ExecutionQueue(max_concurrent=3)
        await queue.start()

        # Add execution to queue
        queued = await queue.enqueue(
            playbook_path="my_playbook.yaml",
            priority=ExecutionPriority.HIGH
        )

        # Check queue status
        status = queue.get_status()
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        execution_callback: Callable | None = None,
    ):
        """
        Initialize execution queue

        Args:
            max_concurrent: Maximum concurrent executions
            execution_callback: Async function to call when executing
        """
        self.max_concurrent = max_concurrent
        self.execution_callback = execution_callback

        self._queue: asyncio.PriorityQueue[QueuedExecution] = asyncio.PriorityQueue()
        self._running: dict[str, QueuedExecution] = {}
        self._completed: list[QueuedExecution] = []
        self._lock = asyncio.Lock()
        self._running_task: asyncio.Task | None = None
        self._shutdown = False

        logger.info(f"ExecutionQueue initialized with max_concurrent={max_concurrent}")

    async def start(self) -> None:
        """Start the queue processor"""
        if self._running_task is not None:
            return

        self._shutdown = False
        self._running_task = asyncio.create_task(self._process_queue())
        logger.info("ExecutionQueue processor started")

    async def stop(self) -> None:
        """Stop the queue processor"""
        self._shutdown = True
        if self._running_task:
            self._running_task.cancel()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
            self._running_task = None
        logger.info("ExecutionQueue processor stopped")

    async def enqueue(
        self,
        playbook_path: str,
        parameters: dict[str, Any] | None = None,
        gateway_url: str | None = None,
        credential_name: str | None = None,
        priority: ExecutionPriority = ExecutionPriority.NORMAL,
    ) -> QueuedExecution:
        """
        Add a playbook execution to the queue

        Args:
            playbook_path: Path to playbook YAML
            parameters: Playbook parameters
            gateway_url: Gateway URL for execution
            credential_name: Credential to use
            priority: Execution priority

        Returns:
            QueuedExecution object
        """
        execution = QueuedExecution(
            playbook_path=playbook_path,
            parameters=parameters or {},
            gateway_url=gateway_url,
            credential_name=credential_name,
            priority=priority,
        )

        await self._queue.put(execution)
        logger.info(f"Queued execution {execution.id} for {playbook_path} (priority={priority.name})")

        return execution

    async def cancel(self, execution_id: str) -> bool:
        """
        Cancel a queued execution

        Args:
            execution_id: ID of execution to cancel

        Returns:
            True if cancelled, False if not found or already running
        """
        async with self._lock:
            # Can't cancel running executions through queue
            if execution_id in self._running:
                logger.warning(f"Cannot cancel running execution {execution_id}")
                return False

            # Need to rebuild queue without the cancelled item
            items = []
            found = False

            while not self._queue.empty():
                try:
                    item = self._queue.get_nowait()
                    if item.id == execution_id:
                        item.state = ExecutionState.CANCELLED
                        item.completed_at = datetime.now(UTC)
                        self._completed.append(item)
                        found = True
                        logger.info(f"Cancelled queued execution {execution_id}")
                    else:
                        items.append(item)
                except asyncio.QueueEmpty:
                    break

            # Re-add non-cancelled items
            for item in items:
                await self._queue.put(item)

            return found

    def get_status(self) -> dict:
        """
        Get queue status

        Returns:
            Dictionary with queue statistics
        """
        return {
            "max_concurrent": self.max_concurrent,
            "queued_count": self._queue.qsize(),
            "running_count": len(self._running),
            "completed_count": len(self._completed),
            "available_slots": max(0, self.max_concurrent - len(self._running)),
            "running": [e.to_dict() for e in self._running.values()],
            "recent_completed": [e.to_dict() for e in self._completed[-10:]],  # Last 10
        }

    def get_queued(self) -> list[QueuedExecution]:
        """Get list of queued executions (read-only snapshot)"""
        # Note: PriorityQueue doesn't support iteration, so this returns empty
        # In production, we'd use a different data structure or maintain a separate list
        return []

    def get_running(self) -> list[QueuedExecution]:
        """Get list of running executions"""
        return list(self._running.values())

    async def _process_queue(self) -> None:
        """Background task to process queued executions"""
        while not self._shutdown:
            try:
                # Wait for available slot
                if len(self._running) >= self.max_concurrent:
                    await asyncio.sleep(0.5)
                    continue

                # Try to get next execution (with timeout to allow shutdown)
                try:
                    execution = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Start execution
                asyncio.create_task(self._run_execution(execution))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in queue processor: {e}")
                await asyncio.sleep(1.0)

    async def _run_execution(self, execution: QueuedExecution) -> None:
        """Run a single execution"""
        async with self._lock:
            execution.state = ExecutionState.RUNNING
            execution.started_at = datetime.now(UTC)
            self._running[execution.id] = execution

        logger.info(f"Starting execution {execution.id} for {execution.playbook_path}")

        try:
            if self.execution_callback:
                result = await self.execution_callback(execution)
                execution.execution_id = result.get("execution_id") if isinstance(result, dict) else None

            execution.state = ExecutionState.COMPLETED
            logger.info(f"Completed execution {execution.id}")

        except Exception as e:
            execution.state = ExecutionState.FAILED
            execution.error_message = str(e)
            logger.error(f"Failed execution {execution.id}: {e}")

        finally:
            execution.completed_at = datetime.now(UTC)
            async with self._lock:
                del self._running[execution.id]
                self._completed.append(execution)

                # Limit completed history
                if len(self._completed) > 100:
                    self._completed = self._completed[-100:]


# Global queue instance
_execution_queue: ExecutionQueue | None = None


def get_execution_queue() -> ExecutionQueue:
    """Get the global execution queue instance"""
    global _execution_queue
    if _execution_queue is None:
        _execution_queue = ExecutionQueue()
    return _execution_queue


async def initialize_execution_queue(
    max_concurrent: int = 3,
    execution_callback: Callable | None = None,
) -> ExecutionQueue:
    """Initialize and start the global execution queue"""
    global _execution_queue
    _execution_queue = ExecutionQueue(
        max_concurrent=max_concurrent,
        execution_callback=execution_callback,
    )
    await _execution_queue.start()
    return _execution_queue

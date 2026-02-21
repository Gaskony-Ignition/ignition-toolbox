"""
Execution Manager - Centralized execution lifecycle management

Manages active executions, background tasks, and TTL-based cleanup.
Replaces module-level globals from app.py with proper encapsulation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable

from ignition_toolkit.playbook.engine import PlaybookEngine

logger = logging.getLogger(__name__)


class ExecutionManager:
    """
    Manages execution lifecycle and state

    Responsibilities:
    - Track active executions
    - Spawn and manage background tasks
    - Cleanup expired executions
    - Provide thread-safe execution access
    """

    def __init__(self, ttl_minutes: int = 30):
        """
        Initialize execution manager

        Args:
            ttl_minutes: Time-to-live for completed executions (default: 30)
        """
        self._active_engines: dict[str, PlaybookEngine] = {}
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._completion_times: dict[str, datetime] = {}
        self._ttl_minutes = ttl_minutes
        self._lock = asyncio.Lock()

    async def start_execution(
        self,
        execution_id: str,
        engine: PlaybookEngine,
        runner: Callable[[], asyncio.Task],
    ) -> None:
        """
        Register and start new execution

        Args:
            execution_id: Unique execution identifier
            engine: PlaybookEngine instance
            runner: Async function that executes the playbook
        """
        async with self._lock:
            self._active_engines[execution_id] = engine
            task = asyncio.create_task(runner())
            self._active_tasks[execution_id] = task
            logger.info(f"Started execution {execution_id}")

    def get_engine(self, execution_id: str) -> PlaybookEngine | None:
        """
        Get active engine by ID

        Args:
            execution_id: Execution UUID

        Returns:
            PlaybookEngine if active, None otherwise
        """
        return self._active_engines.get(execution_id)

    def get_task(self, execution_id: str) -> asyncio.Task | None:
        """
        Get active task by ID

        Args:
            execution_id: Execution UUID

        Returns:
            asyncio.Task if active, None otherwise
        """
        return self._active_tasks.get(execution_id)

    async def cancel_execution(self, execution_id: str) -> dict | None:
        """
        Cancel active execution

        Args:
            execution_id: Execution UUID

        Returns:
            Dict with cancellation details if found, None if not found.
            Dict keys: 'task_was_done' (bool) - whether the asyncio task had already completed
        """
        engine = self._active_engines.get(execution_id)
        task = self._active_tasks.get(execution_id)

        if not engine or not task:
            logger.warning(f"Cannot cancel {execution_id} - not found in active executions")
            return None

        task_was_done = task.done()
        logger.info(f"Cancelling execution {execution_id} (task done: {task_was_done})")

        # Cancel engine first (graceful shutdown + closes browser)
        await engine.cancel()
        logger.info(f"Engine cancellation complete for {execution_id}")

        # Then cancel the asyncio task to interrupt execution
        if not task_was_done:
            task.cancel()
            logger.info(f"Task cancelled for {execution_id}")
        else:
            logger.warning(f"Task already done for {execution_id}, skipping task.cancel()")

        # Mark as completed for TTL tracking
        self._mark_completed(execution_id)

        logger.info(f"✅ Cancellation complete for {execution_id}")
        return {"task_was_done": task_was_done}

    def _mark_completed(self, execution_id: str) -> None:
        """
        Mark execution as completed for TTL tracking

        Args:
            execution_id: Execution UUID
        """
        self._completion_times[execution_id] = datetime.now()

    def mark_completed(self, execution_id: str) -> None:
        """
        Public method to mark execution as completed

        Args:
            execution_id: Execution UUID
        """
        self._mark_completed(execution_id)

    def remove_task(self, execution_id: str) -> None:
        """
        Remove task reference (called when task completes)

        Args:
            execution_id: Execution UUID
        """
        if execution_id in self._active_tasks:
            del self._active_tasks[execution_id]

    async def cleanup_expired(self) -> int:
        """
        Remove executions older than TTL

        Returns:
            Number of executions cleaned up
        """
        cutoff = datetime.now() - timedelta(minutes=self._ttl_minutes)
        expired = [
            eid
            for eid, completed_at in self._completion_times.items()
            if completed_at < cutoff
        ]

        async with self._lock:
            for eid in expired:
                self._active_engines.pop(eid, None)
                self._active_tasks.pop(eid, None)
                self._completion_times.pop(eid)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired executions")

        return len(expired)

    def list_active(self) -> list[str]:
        """
        Get list of active execution IDs

        Returns:
            List of execution IDs
        """
        return list(self._active_engines.keys())

    def is_active(self, execution_id: str) -> bool:
        """
        Check if execution is active

        Args:
            execution_id: Execution UUID

        Returns:
            True if execution is active, False otherwise
        """
        return execution_id in self._active_engines

    def is_expired(self, execution_id: str) -> bool:
        """
        Check if execution has exceeded TTL

        Args:
            execution_id: Execution UUID

        Returns:
            True if expired, False otherwise
        """
        if completion_time := self._completion_times.get(execution_id):
            elapsed_minutes = (datetime.now() - completion_time).total_seconds() / 60
            return elapsed_minutes > self._ttl_minutes
        return False

    async def cleanup(self) -> None:
        """
        Cleanup all active executions (called on shutdown)
        """
        logger.info("Cleaning up ExecutionManager...")

        # Cancel all active tasks
        tasks_to_cancel = list(self._active_tasks.values())
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete cancellation
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        # Clear all state
        self._active_engines.clear()
        self._active_tasks.clear()
        self._completion_times.clear()

        logger.info("ExecutionManager cleanup complete")

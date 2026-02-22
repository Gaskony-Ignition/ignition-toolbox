"""
Cancellation utilities for playbook execution

Provides reusable utilities for implementing responsive cancellation
in all step types. All long-running operations should use these utilities
to ensure consistent cancellation behavior.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def cancellable_sleep(seconds: float, check_interval: float = 0.5) -> None:
    """
    Sleep that respects cancellation signals

    Instead of sleeping for the full duration, sleeps in small intervals.
    When task.cancel() is called, asyncio.sleep() will automatically raise
    CancelledError at the next interval, ensuring cancellation is detected
    within check_interval seconds.

    Args:
        seconds: Total time to sleep in seconds
        check_interval: How often to wake up and check (default: 0.5s)

    Raises:
        asyncio.CancelledError: If task is cancelled during sleep

    Example:
        # Instead of:
        await asyncio.sleep(30)

        # Use:
        await cancellable_sleep(30)  # Responds to cancel within 0.5s
    """
    remaining = seconds
    while remaining > 0:
        # Sleep for minimum of check_interval or remaining time
        # asyncio.sleep() will automatically raise CancelledError if task.cancel() is called
        sleep_time = min(check_interval, remaining)

        try:
            await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logger.debug(f"Sleep cancelled after {seconds - remaining:.1f}s of {seconds}s")
            raise

        remaining -= sleep_time


async def cancellable_poll(
    condition: Callable[[], bool],
    timeout: float,
    poll_interval: float = 1.0,
    error_message: str = "Timeout waiting for condition",
) -> None:
    """
    Poll a condition with cancellation support

    Checks a condition repeatedly until it returns True or timeout is reached.
    Cancellation happens automatically through cancellable_sleep().

    Args:
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds (default: 1.0)
        error_message: Error message if timeout is reached

    Raises:
        asyncio.CancelledError: If task is cancelled during polling
        TimeoutError: If condition not met within timeout

    Example:
        # Wait for element to be visible
        await cancellable_poll(
            condition=lambda: element.is_visible(),
            timeout=30,
            poll_interval=0.5,
            error_message="Element not visible"
        )
    """
    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        # Check condition
        if condition():
            return

        # Sleep - will raise CancelledError if task.cancel() is called
        try:
            await cancellable_sleep(poll_interval)
        except asyncio.CancelledError:
            logger.debug("Poll cancelled during sleep")
            raise

    # Timeout reached
    raise TimeoutError(error_message)


async def with_cancellation_check(coro: Any) -> Any:
    """
    Wrap a coroutine to ensure cancellation propagates

    Simply awaits the coroutine. If task.cancel() is called, the await
    will automatically raise CancelledError. Use this for operations that
    might not respond to cancellation themselves (like Playwright operations).

    Args:
        coro: Coroutine to execute

    Returns:
        Result of the coroutine

    Raises:
        asyncio.CancelledError: If task is cancelled

    Example:
        # Wrap Playwright operations
        result = await with_cancellation_check(
            page.click(selector)
        )
    """
    try:
        # Execute the operation - will raise CancelledError if task.cancel() is called
        result = await coro
        return result

    except asyncio.CancelledError:
        logger.debug("Operation cancelled during execution")
        raise


class CancellationMixin:
    """
    Mixin to add cancellation checking to executors

    Add this mixin to executor classes to get consistent cancellation
    behavior across all step types. Note: In most cases, you don't need
    explicit cancellation checks - asyncio will automatically raise
    CancelledError at await points when task.cancel() is called.

    Example:
        class BrowserExecutor(CancellationMixin):
            async def execute_click(self, params):
                # Use cancellable_sleep between operations
                await cancellable_sleep(0.1)
                await page.click(selector)
    """

    async def check_cancelled(self, message: str = "Operation cancelled") -> None:
        """
        Yield control to allow cancellation to propagate

        This method simply yields control back to the event loop by sleeping
        for 0 seconds, which allows CancelledError to be raised if the task
        was cancelled.

        Args:
            message: Log message if cancelled (logged only if cancelled)

        Raises:
            asyncio.CancelledError: If task is cancelled
        """
        try:
            await asyncio.sleep(0)  # Yield control - will raise CancelledError if cancelled
        except asyncio.CancelledError:
            logger.info(message)
            raise

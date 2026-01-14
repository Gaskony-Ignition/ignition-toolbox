"""
State manager - Execution state and control signals

Handles pause, resume, skip functionality for playbook execution.
"""

import asyncio
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ControlSignal(str, Enum):
    """Control signals for execution"""

    NONE = "none"
    PAUSE = "pause"
    RESUME = "resume"
    SKIP = "skip"
    CANCEL = "cancel"
    DEBUG_PAUSE = "debug_pause"  # Auto-pause triggered by failure in debug mode


class StateManager:
    """
    Manage execution state and control signals

    Provides thread-safe control over playbook execution with pause/resume/skip/cancel.

    Example:
        state_mgr = StateManager()

        # In execution thread
        await state_mgr.check_control_signal()

        # From API/UI
        state_mgr.pause()
        state_mgr.resume()
        state_mgr.skip_current_step()
    """

    def __init__(self):
        """Initialize state manager"""
        self._signal = ControlSignal.NONE
        self._signal_event = asyncio.Event()
        self._signal_event.set()  # Start in running state
        self._lock = asyncio.Lock()
        self._skip_requested = False
        self._skip_back_requested = False
        self._debug_mode_enabled = False
        self._debug_context = {}  # Stores screenshot, HTML, step info on failure

    async def check_control_signal(self) -> ControlSignal:
        """
        Check for control signals and handle them

        Should be called at appropriate points in execution loop.

        Returns:
            Current control signal

        Raises:
            asyncio.CancelledError: If execution should be cancelled
        """
        async with self._lock:
            current_signal = self._signal

            # Handle pause
            if current_signal == ControlSignal.PAUSE:
                logger.info("Execution paused, waiting for resume...")
                self._signal_event.clear()

        # Wait for resume (outside lock to allow other operations)
        if current_signal == ControlSignal.PAUSE:
            await self._signal_event.wait()
            async with self._lock:
                current_signal = self._signal

        # Handle cancel
        if current_signal == ControlSignal.CANCEL:
            logger.info("Execution cancelled")
            raise asyncio.CancelledError("Execution cancelled by user")

        return current_signal

    def is_skip_requested(self) -> bool:
        """
        Check if current step should be skipped

        Returns:
            True if skip requested
        """
        return self._skip_requested

    def clear_skip(self) -> None:
        """Clear skip flag after processing"""
        self._skip_requested = False

    def is_skip_back_requested(self) -> bool:
        """
        Check if execution should skip back to previous step

        Returns:
            True if skip back requested
        """
        return self._skip_back_requested

    def clear_skip_back(self) -> None:
        """Clear skip back flag after processing"""
        self._skip_back_requested = False

    async def pause(self) -> None:
        """Request execution to pause after current step"""
        async with self._lock:
            if self._signal != ControlSignal.PAUSE:
                logger.info("Pause requested")
                self._signal = ControlSignal.PAUSE
                self._signal_event.clear()

    async def resume(self) -> None:
        """Resume paused execution"""
        async with self._lock:
            if self._signal == ControlSignal.PAUSE:
                logger.info("Resuming execution")
                self._signal = ControlSignal.NONE
                self._signal_event.set()

    async def skip_current_step(self) -> None:
        """Skip current step and continue"""
        async with self._lock:
            logger.info("Skip current step requested")
            self._skip_requested = True
            # If paused, also resume
            if self._signal == ControlSignal.PAUSE:
                self._signal = ControlSignal.NONE
                self._signal_event.set()

    async def skip_back_step(self) -> None:
        """Skip back to previous step (re-run from previous step)"""
        async with self._lock:
            logger.info("Skip back to previous step requested")
            self._skip_back_requested = True
            # If paused, also resume
            if self._signal == ControlSignal.PAUSE:
                self._signal = ControlSignal.NONE
                self._signal_event.set()

    async def cancel(self) -> None:
        """Cancel execution"""
        async with self._lock:
            logger.info("Cancel requested")
            self._signal = ControlSignal.CANCEL
            self._signal_event.set()  # Unblock any waiting

    def reset(self) -> None:
        """Reset state manager for new execution"""
        self._signal = ControlSignal.NONE
        self._signal_event.set()
        self._skip_requested = False
        self._skip_back_requested = False
        self._debug_context = {}

    def is_paused(self) -> bool:
        """
        Check if execution is currently paused

        Returns:
            True if paused
        """
        return self._signal == ControlSignal.PAUSE

    def is_cancelled(self) -> bool:
        """
        Check if execution is cancelled

        Returns:
            True if cancelled
        """
        return self._signal == ControlSignal.CANCEL

    def get_status(self) -> dict:
        """
        Get current state manager status

        Returns:
            Status dictionary
        """
        return {
            "signal": self._signal.value,
            "paused": self.is_paused(),
            "cancelled": self.is_cancelled(),
            "skip_requested": self._skip_requested,
            "debug_mode_enabled": self._debug_mode_enabled,
            "has_debug_context": bool(self._debug_context),
        }

    def enable_debug_mode(self) -> None:
        """Enable debug mode - auto-pause on failures"""
        self._debug_mode_enabled = True
        logger.info("Debug mode enabled - will auto-pause on failures")

    def disable_debug_mode(self) -> None:
        """Disable debug mode"""
        self._debug_mode_enabled = False
        self._debug_context = {}
        logger.info("Debug mode disabled")

    def is_debug_mode_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return self._debug_mode_enabled

    async def trigger_debug_pause(self, context: dict) -> None:
        """
        Trigger debug pause due to failure

        Args:
            context: Debug context (screenshot, HTML, step info, error)
        """
        async with self._lock:
            self._debug_context = context
            self._signal = ControlSignal.DEBUG_PAUSE
            self._signal_event.clear()
            logger.info(f"Debug pause triggered: {context.get('error', 'Unknown error')}")

    def get_debug_context(self) -> dict:
        """
        Get debug context from last failure

        Returns:
            Debug context dictionary
        """
        return self._debug_context.copy()

    def clear_debug_context(self) -> None:
        """Clear debug context"""
        self._debug_context = {}

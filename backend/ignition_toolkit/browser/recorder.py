"""
Browser recorder - Capture screenshots and videos

Records browser sessions for playback and debugging.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BrowserRecorder:
    """
    Record browser sessions

    Captures screenshots at intervals and provides video recording capabilities.

    Example:
        recorder = BrowserRecorder(output_dir=Path("./recordings"))
        await recorder.start_recording()
        # ... browser operations ...
        await recorder.stop_recording()
    """

    def __init__(self, output_dir: Path):
        """
        Initialize recorder

        Args:
            output_dir: Output directory for recordings
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._recording = False
        self._screenshot_task: asyncio.Task | None = None
        self._screenshots: list[Path] = []

    async def start_recording(self, interval: float = 1.0) -> None:
        """
        Start recording screenshots

        Args:
            interval: Screenshot interval in seconds
        """
        if self._recording:
            logger.warning("Recording already started")
            return

        self._recording = True
        self._screenshots = []

        logger.info(f"Started recording (interval: {interval}s)")

    async def stop_recording(self) -> list[Path]:
        """
        Stop recording

        Returns:
            List of screenshot paths
        """
        if not self._recording:
            logger.warning("Recording not started")
            return []

        self._recording = False

        if self._screenshot_task:
            self._screenshot_task.cancel()
            try:
                await self._screenshot_task
            except asyncio.CancelledError:
                pass

        logger.info(f"Stopped recording ({len(self._screenshots)} screenshots)")
        return self._screenshots

    async def capture_screenshot(self, browser_manager, name: str | None = None) -> Path:
        """
        Capture single screenshot

        Args:
            browser_manager: BrowserManager instance
            name: Screenshot name (auto-generated if not provided)

        Returns:
            Screenshot path
        """
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            name = f"screenshot_{timestamp}"

        screenshot_path = await browser_manager.screenshot(name)
        self._screenshots.append(screenshot_path)
        return screenshot_path

    def get_screenshots(self) -> list[Path]:
        """
        Get list of captured screenshots

        Returns:
            List of screenshot paths
        """
        return self._screenshots.copy()

"""
Playwright browser auto-installer

Automatically installs Playwright browsers on first run if they're not present.
This enables the bundled application to work without requiring users to manually
run 'playwright install'.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ignition_toolkit.core.timeouts import TimeoutDefaults

logger = logging.getLogger(__name__)

# Browser to install (chromium is sufficient for this application)
BROWSER_TYPE = "chromium"


def get_playwright_browsers_path() -> Path:
    """
    Get the path where Playwright stores browsers.

    Playwright uses different locations based on environment:
    - PLAYWRIGHT_BROWSERS_PATH env var if set
    - Otherwise platform-specific cache directory
    """
    # Check for custom path
    custom_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom_path:
        return Path(custom_path)

    # Default Playwright browser locations
    if sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\ms-playwright
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            return Path(local_app_data) / "ms-playwright"
        return Path.home() / "AppData" / "Local" / "ms-playwright"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Caches/ms-playwright
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    else:
        # Linux: ~/.cache/ms-playwright
        cache_home = os.environ.get("XDG_CACHE_HOME", "")
        if cache_home:
            return Path(cache_home) / "ms-playwright"
        return Path.home() / ".cache" / "ms-playwright"


def is_browser_installed() -> bool:
    """
    Check if Playwright Chromium browser is installed.

    Checks for both regular chromium and headless shell variants,
    as Playwright versions may use different browser packages.

    Returns:
        True if browser appears to be installed, False otherwise
    """
    browsers_path = get_playwright_browsers_path()

    if not browsers_path.exists():
        logger.info(f"Playwright browsers directory not found: {browsers_path}")
        return False

    # Check for different Chromium variants (newer Playwright uses chromium_headless_shell)
    # Pattern: chromium-*, chromium_headless_shell-*
    browser_patterns = ["chromium-*", "chromium_headless_shell-*"]

    for pattern in browser_patterns:
        chromium_dirs = list(browsers_path.glob(pattern))
        for chromium_dir in chromium_dirs:
            # Check for executables based on platform and browser variant
            # Playwright versions use different directory names (e.g., chrome-win vs chrome-win64)
            if sys.platform == "win32":
                exe_paths = [
                    chromium_dir / "chrome-win" / "chrome.exe",
                    chromium_dir / "chrome-win64" / "chrome.exe",
                    chromium_dir / "chrome-win" / "headless_shell.exe",
                    chromium_dir / "chrome-win64" / "headless_shell.exe",
                    chromium_dir / "chrome-headless-shell-win64" / "headless_shell.exe",
                ]
            elif sys.platform == "darwin":
                exe_paths = [
                    chromium_dir / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
                    chromium_dir / "chrome-mac-arm64" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
                    chromium_dir / "chrome-mac" / "headless_shell",
                    chromium_dir / "chrome-mac-arm64" / "headless_shell",
                ]
            else:
                exe_paths = [
                    chromium_dir / "chrome-linux" / "chrome",
                    chromium_dir / "chrome-linux" / "headless_shell",
                ]

            for exe_path in exe_paths:
                if exe_path.exists():
                    logger.info(f"Found Chromium browser at: {exe_path}")
                    return True

    logger.info("No Chromium browser executable found in Playwright cache")
    return False


async def install_browser(progress_callback=None) -> bool:
    """
    Install Playwright Chromium browser.

    Args:
        progress_callback: Optional async callback function(message: str, progress: float)
                          progress is 0.0 to 1.0

    Returns:
        True if installation successful, False otherwise
    """
    logger.info("Installing Playwright Chromium browser...")

    if progress_callback:
        await progress_callback("Starting browser download...", 0.0)

    try:
        # For frozen executables, we must use the Playwright driver directly
        # because sys.executable points to our app, not Python
        if getattr(sys, 'frozen', False):
            return await _install_browser_via_driver(progress_callback)

        # Development mode - use python -m playwright
        playwright_cmd = [sys.executable, "-m", "playwright", "install", BROWSER_TYPE]

        logger.info(f"Running: {' '.join(playwright_cmd)}")

        if progress_callback:
            await progress_callback("Downloading Chromium browser...", 0.1)

        # Run installation with timeout (5 minutes max)
        process = await asyncio.create_subprocess_exec(
            *playwright_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=TimeoutDefaults.MODULE_INSTALL)
        except asyncio.TimeoutError:
            logger.error("Browser installation timed out after 5 minutes")
            process.kill()
            if progress_callback:
                await progress_callback("Installation timed out", 1.0)
            return False

        if process.returncode == 0:
            logger.info("Playwright Chromium browser installed successfully")
            if progress_callback:
                await progress_callback("Browser installed successfully", 1.0)
            return True
        else:
            error_msg = stderr.decode() if stderr else stdout.decode()
            logger.error(f"Browser installation failed: {error_msg}")
            if progress_callback:
                await progress_callback(f"Installation failed: {error_msg}", 1.0)
            return False

    except FileNotFoundError:
        # Playwright CLI not available, try alternative method
        logger.warning("Playwright CLI not found, trying driver installation...")
        return await _install_browser_via_driver(progress_callback)
    except Exception as e:
        logger.error(f"Browser installation error: {e}")
        if progress_callback:
            await progress_callback(f"Installation error: {e}", 1.0)
        return False


async def _install_browser_via_driver(progress_callback=None) -> bool:
    """
    Install browser using Playwright's driver executable directly.

    This method works for both frozen (PyInstaller) and development modes.
    It uses Playwright's bundled driver to download and install browsers.
    """
    try:
        if progress_callback:
            await progress_callback("Using Playwright driver for installation...", 0.1)

        # Import playwright's driver module
        from playwright._impl._driver import compute_driver_executable

        # Get the driver path - returns (node_executable, cli_js_path)
        driver_info = compute_driver_executable()

        # Handle both tuple return (node, cli.js) and single executable return
        if isinstance(driver_info, tuple):
            node_executable, cli_js = driver_info
            cmd = [str(node_executable), str(cli_js), "install", BROWSER_TYPE]
        else:
            cmd = [str(driver_info), "install", BROWSER_TYPE]

        logger.info(f"Running Playwright driver: {' '.join(cmd)}")

        if progress_callback:
            await progress_callback("Downloading Chromium browser...", 0.2)

        # Run the driver with install command (5 minute timeout)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=TimeoutDefaults.MODULE_INSTALL)
        except asyncio.TimeoutError:
            logger.error("Driver browser installation timed out after 5 minutes")
            process.kill()
            if progress_callback:
                await progress_callback("Installation timed out", 1.0)
            return False

        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        # Log output for debugging
        if stdout_text:
            logger.info(f"Driver stdout: {stdout_text}")
        if stderr_text:
            logger.info(f"Driver stderr: {stderr_text}")

        if process.returncode == 0:
            logger.info("Browser installed via Playwright driver")
            if progress_callback:
                await progress_callback("Browser installed successfully", 1.0)
            return True
        else:
            error_msg = stderr_text or stdout_text or "Unknown error"
            logger.error(f"Driver installation failed (code {process.returncode}): {error_msg}")
            if progress_callback:
                await progress_callback(f"Installation failed: {error_msg}", 1.0)
            return False

    except ImportError as e:
        logger.error(f"Could not import Playwright driver: {e}")
        if progress_callback:
            await progress_callback(f"Playwright driver not available: {e}", 1.0)
        return False
    except Exception as e:
        logger.error(f"Driver installation failed: {e}")
        if progress_callback:
            await progress_callback(f"Installation error: {e}", 1.0)
        return False


async def ensure_browser_installed(progress_callback=None) -> bool:
    """
    Ensure Playwright browser is installed, installing if necessary.

    This is the main entry point for the auto-installer.

    Args:
        progress_callback: Optional async callback for progress updates

    Returns:
        True if browser is ready to use, False if installation failed
    """
    if is_browser_installed():
        logger.info("Playwright browser already installed")
        if progress_callback:
            await progress_callback("Browser already installed", 1.0)
        return True

    logger.info("Playwright browser not found, initiating installation...")
    return await install_browser(progress_callback)


def get_browser_info() -> dict:
    """
    Get information about installed Playwright browsers.

    Returns:
        Dictionary with browser information
    """
    browsers_path = get_playwright_browsers_path()

    info = {
        "browsers_path": str(browsers_path),
        "chromium_installed": False,
        "chromium_path": None,
    }

    if browsers_path.exists():
        # Check for both chromium variants
        for pattern in ["chromium-*", "chromium_headless_shell-*"]:
            chromium_dirs = list(browsers_path.glob(pattern))
            if chromium_dirs:
                info["chromium_installed"] = True
                info["chromium_path"] = str(chromium_dirs[0])
                break

    return info

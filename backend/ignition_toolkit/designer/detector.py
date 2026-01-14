"""
Installation path detection for Ignition Designer

Auto-detects Designer installation across different platforms.
"""

import logging
import os
import platform
from pathlib import Path

logger = logging.getLogger(__name__)


def detect_designer_installation() -> Path | None:
    """
    Auto-detect Ignition Designer installation path

    Searches common installation locations based on platform:
    - Windows: Program Files, Program Files (x86)
    - Linux: /opt, /usr/local, ~/.local
    - WSL2: Windows paths accessible via /mnt/c

    Returns:
        Path to Designer installation directory, or None if not found
    """
    system = platform.system()
    logger.info(f"Detecting Designer installation on {system}...")

    if system == "Windows":
        return _detect_windows()
    elif system == "Linux":
        # Check if running in WSL
        if _is_wsl():
            logger.info("WSL detected, checking both Linux and Windows paths")
            # Try Linux paths first
            linux_path = _detect_linux()
            if linux_path:
                return linux_path
            # Fall back to Windows paths via /mnt/c
            return _detect_wsl()
        else:
            return _detect_linux()
    else:
        logger.warning(f"Unsupported platform: {system}")
        return None


def _detect_windows() -> Path | None:
    """Detect Designer on Windows"""
    search_paths = [
        Path(r"C:\Program Files\Inductive Automation\Designer Launcher"),
        Path(r"C:\Program Files (x86)\Inductive Automation\Designer Launcher"),
        Path(r"C:\Program Files\Inductive Automation\Ignition Designer Launcher"),  # Legacy path
        Path(r"C:\Program Files (x86)\Inductive Automation\Ignition Designer Launcher"),  # Legacy path
        Path(os.path.expanduser(r"~\AppData\Local\Inductive Automation\Designer Launcher")),
    ]

    for path in search_paths:
        # Look for designerlauncher.exe (Ignition 8.3+)
        launcher = path / "designerlauncher.exe"
        if launcher.exists():
            logger.info(f"Found Designer at: {path}")
            return path

    logger.warning("Designer not found in standard Windows locations")
    return None


def _detect_linux() -> Path | None:
    """Detect Designer on Linux"""
    search_paths = [
        Path("/opt/ignition-designer"),
        Path("/usr/local/ignition-designer"),
        Path.home() / ".local" / "ignition-designer",
        Path.home() / "ignition-designer",
    ]

    for path in search_paths:
        # Look for designer-launcher script or JAR
        if path.exists():
            # Check for common Designer launcher files
            if (path / "designer-launcher").exists() or \
               (path / "designer.jar").exists() or \
               any(path.glob("designer-launcher*")):
                logger.info(f"Found Designer at: {path}")
                return path

    logger.warning("Designer not found in standard Linux locations")
    return None


def _detect_wsl() -> Path | None:
    """Detect Designer on WSL (Windows paths via /mnt/c)"""
    search_paths = [
        Path("/mnt/c/Program Files/Inductive Automation/Designer Launcher"),
        Path("/mnt/c/Program Files (x86)/Inductive Automation/Designer Launcher"),
        Path("/mnt/c/Program Files/Inductive Automation/Ignition Designer Launcher"),  # Legacy
        Path("/mnt/c/Program Files (x86)/Inductive Automation/Ignition Designer Launcher"),  # Legacy
    ]

    for path in search_paths:
        launcher = path / "designerlauncher.exe"
        if launcher.exists():
            logger.info(f"Found Designer (WSL) at: {path}")
            return path

    logger.warning("Designer not found in WSL Windows paths")
    return None


def _is_wsl() -> bool:
    """
    Check if running in WSL

    Returns:
        True if running in WSL environment
    """
    try:
        # Check for WSL-specific indicators
        with open("/proc/version", "r") as f:
            version = f.read().lower()
            return "microsoft" in version or "wsl" in version
    except:
        return False


def get_java_command() -> str:
    """
    Get the appropriate Java command for the platform

    Returns:
        Java command path (java, javaws, or full path)
    """
    system = platform.system()

    # Try to find java in PATH
    java_path = _find_executable("java")
    if java_path:
        return java_path

    # Platform-specific Java locations
    if system == "Windows":
        common_paths = [
            r"C:\Program Files\Java\jre*\bin\java.exe",
            r"C:\Program Files (x86)\Java\jre*\bin\java.exe",
        ]
        for pattern in common_paths:
            matches = list(Path(pattern).parent.parent.parent.glob(pattern))
            if matches:
                return str(matches[0])

    elif system == "Linux":
        common_paths = [
            "/usr/bin/java",
            "/usr/lib/jvm/default-java/bin/java",
            "/opt/java/bin/java",
        ]
        for path in common_paths:
            if Path(path).exists():
                return path

    # Default to just "java" and hope it's in PATH
    logger.warning("Could not find Java installation, using 'java' command")
    return "java"


def _find_executable(name: str) -> str | None:
    """
    Find executable in PATH

    Args:
        name: Executable name (e.g., "java", "javaws")

    Returns:
        Full path to executable, or None if not found
    """
    import shutil
    return shutil.which(name)

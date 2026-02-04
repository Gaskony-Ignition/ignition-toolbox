"""
Docker and WSL detection utilities for CloudDesigner.

Handles:
- Docker executable detection on Windows, Linux, and WSL
- WSL Docker command caching
- Path conversion between Windows and WSL
- Docker host IP detection for container connectivity
"""

import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Windows-specific subprocess flag to hide console window
# On non-Windows platforms, use 0 (no flags)
CREATION_FLAGS = (
    subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
)

# Cache for the working WSL Docker command prefix
# This stores the command that successfully found Docker (e.g., ["wsl", "-d", "Ubuntu", "docker"])
_wsl_docker_command: list[str] | None = None

# Cache to avoid repeated Docker detection on every status poll
_docker_detection_cache: dict[str, str | None] = {}
_docker_detection_done: bool = False


def is_wsl() -> bool:
    """
    Check if running inside Windows Subsystem for Linux (WSL).

    Returns:
        True if running in WSL, False otherwise
    """
    if platform.system() != "Linux":
        return False

    try:
        with open("/proc/version", "r", encoding="utf-8", errors="replace") as f:
            version_info = f.read().lower()
            return "microsoft" in version_info or "wsl" in version_info
    except OSError:
        return False


def check_wsl_docker() -> tuple[bool, str | None]:
    """
    Check if Docker is available inside WSL (for Windows with WSL2 backend).

    Tries multiple approaches:
    1. wsl docker --version (default distro)
    2. wsl -e docker --version (explicit exec)
    3. wsl -- docker --version (pass-through)
    4. Specific distributions: Ubuntu, Debian, etc.

    Returns:
        Tuple of (available: bool, version: str | None)

    Side effect:
        Sets _wsl_docker_command global with the working command prefix
    """
    global _wsl_docker_command

    current_platform = platform.system()
    logger.debug(f"WSL Docker check - Platform: {current_platform}")

    if current_platform != "Windows":
        logger.debug("WSL Docker check skipped - not on Windows")
        return False, None

    # First check if wsl.exe exists
    wsl_path = shutil.which("wsl")
    if not wsl_path:
        logger.debug("WSL not found in PATH")
        return False, None

    logger.debug(f"WSL found at: {wsl_path}")

    # Different ways to invoke docker via WSL
    # Each entry is (command_to_test, docker_command_prefix)
    # Include sudo variants for when Docker requires root access
    wsl_commands = [
        (["wsl", "docker", "--version"], ["wsl", "docker"]),
        (["wsl", "-e", "docker", "--version"], ["wsl", "-e", "docker"]),
        (["wsl", "--", "docker", "--version"], ["wsl", "--", "docker"]),
        # Try with sudo (for Docker installed as root only)
        (["wsl", "sudo", "docker", "--version"], ["wsl", "sudo", "docker"]),
        (["wsl", "-e", "sudo", "docker", "--version"], ["wsl", "-e", "sudo", "docker"]),
        # Try specific common distributions
        (["wsl", "-d", "Ubuntu", "docker", "--version"], ["wsl", "-d", "Ubuntu", "docker"]),
        (["wsl", "-d", "Ubuntu", "sudo", "docker", "--version"], ["wsl", "-d", "Ubuntu", "sudo", "docker"]),
        (["wsl", "-d", "Ubuntu-22.04", "docker", "--version"], ["wsl", "-d", "Ubuntu-22.04", "docker"]),
        (["wsl", "-d", "Ubuntu-22.04", "sudo", "docker", "--version"], ["wsl", "-d", "Ubuntu-22.04", "sudo", "docker"]),
        (["wsl", "-d", "Ubuntu-24.04", "docker", "--version"], ["wsl", "-d", "Ubuntu-24.04", "docker"]),
        (["wsl", "-d", "Ubuntu-24.04", "sudo", "docker", "--version"], ["wsl", "-d", "Ubuntu-24.04", "sudo", "docker"]),
        (["wsl", "-d", "Debian", "docker", "--version"], ["wsl", "-d", "Debian", "docker"]),
        (["wsl", "-d", "Debian", "sudo", "docker", "--version"], ["wsl", "-d", "Debian", "sudo", "docker"]),
        (["wsl", "-d", "docker-desktop", "docker", "--version"], ["wsl", "-d", "docker-desktop", "docker"]),
    ]

    for test_cmd, docker_prefix in wsl_commands:
        try:
            logger.debug(f"Trying WSL Docker: {' '.join(test_cmd)}")
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,  # Longer timeout for WSL startup
                creationflags=CREATION_FLAGS,
            )
            logger.debug(f"WSL Docker result: returncode={result.returncode}")
            if result.returncode == 0:
                version = result.stdout.strip()
                # Extract distro name for logging if using -d flag
                distro = test_cmd[test_cmd.index("-d") + 1] if "-d" in test_cmd else "default"
                logger.info(f"[CloudDesigner] Docker found via WSL ({distro}): {version}")
                # Cache the working command prefix for future use
                _wsl_docker_command = docker_prefix
                logger.debug(f"Cached WSL Docker command: {_wsl_docker_command}")
                return True, version
            else:
                logger.debug(f"WSL Docker command failed: {result.stderr[:100] if result.stderr else 'no error'}")
        except FileNotFoundError as e:
            logger.debug(f"WSL command not found: {e}")
            return False, None
        except subprocess.TimeoutExpired:
            logger.debug(f"WSL Docker command timed out: {test_cmd}")
        except OSError as e:
            logger.debug(f"WSL Docker check error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error checking WSL Docker: {e}")

    logger.debug("All WSL Docker detection methods failed")
    return False, None


def check_wsl_docker_running() -> bool:
    """
    Check if Docker daemon is running inside WSL.

    Uses the cached WSL Docker command if available.

    Returns:
        True if Docker daemon is accessible via WSL
    """
    global _wsl_docker_command

    if platform.system() != "Windows":
        return False

    # If we have a cached working command, try that first
    if _wsl_docker_command:
        try:
            cmd = _wsl_docker_command + ["info"]
            logger.debug(f"Checking WSL Docker daemon with cached command")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=CREATION_FLAGS,
            )
            if result.returncode == 0:
                logger.debug(f"WSL Docker daemon running via cached command")
                return True
            else:
                logger.debug(f"WSL Docker daemon not running")
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"WSL Docker daemon check failed: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error checking WSL Docker daemon: {e}")

    # Fallback: try multiple approaches including specific distros and sudo
    wsl_commands = [
        ["wsl", "docker", "info"],
        ["wsl", "sudo", "docker", "info"],
        ["wsl", "-d", "Ubuntu", "docker", "info"],
        ["wsl", "-d", "Ubuntu", "sudo", "docker", "info"],
        ["wsl", "-d", "Ubuntu-22.04", "docker", "info"],
        ["wsl", "-d", "Ubuntu-22.04", "sudo", "docker", "info"],
        ["wsl", "-d", "Ubuntu-24.04", "docker", "info"],
        ["wsl", "-d", "Ubuntu-24.04", "sudo", "docker", "info"],
        ["wsl", "-d", "Debian", "docker", "info"],
        ["wsl", "-d", "Debian", "sudo", "docker", "info"],
    ]

    for cmd in wsl_commands:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=CREATION_FLAGS,
            )
            if result.returncode == 0:
                logger.debug(f"WSL Docker daemon running via: {' '.join(cmd)}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"WSL Docker daemon check failed for {cmd}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error checking WSL Docker daemon for {cmd}: {e}")

    return False


def find_docker_executable() -> str | None:
    """
    Find the Docker executable path.

    Checks in order:
    1. Linux PATH first (works for WSL with Docker installed natively)
    2. Linux standard paths: /usr/bin/docker, /usr/local/bin/docker
    3. WSL Windows paths: /mnt/c/Program Files/Docker/...
    4. Native Windows paths (for Windows host)
    5. WSL Docker (for Windows with Docker in WSL2)

    Returns:
        Path to docker executable, or None if not found
    """
    global _docker_detection_done, _docker_detection_cache

    # Return cached result if we've already done detection
    if _docker_detection_done and "docker_path" in _docker_detection_cache:
        return _docker_detection_cache["docker_path"]

    current_platform = platform.system()
    logger.debug(f"Finding Docker executable - Platform: {current_platform}")

    # First, try to find docker in PATH
    docker_path = shutil.which("docker")
    if docker_path:
        logger.debug(f"Docker found in PATH: {docker_path}")
        _docker_detection_cache["docker_path"] = docker_path
        _docker_detection_done = True
        return docker_path

    logger.debug("Docker not found in PATH, checking platform-specific locations")

    # On Linux (including WSL), check standard Linux paths
    if current_platform == "Linux":
        linux_paths = [
            Path("/usr/bin/docker"),
            Path("/usr/local/bin/docker"),
            Path("/snap/bin/docker"),
        ]

        for path in linux_paths:
            if path.exists():
                logger.debug(f"Found Docker at: {path}")
                _docker_detection_cache["docker_path"] = str(path)
                _docker_detection_done = True
                return str(path)

        # If running in WSL, also check Windows Docker Desktop paths via /mnt/c
        if is_wsl():
            wsl_windows_paths = [
                Path("/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"),
                Path("/mnt/c/Program Files/Docker/Docker/resources/bin/docker"),
            ]

            for path in wsl_windows_paths:
                if path.exists():
                    logger.debug(f"Found Docker (WSL Windows) at: {path}")
                    _docker_detection_cache["docker_path"] = str(path)
                    _docker_detection_done = True
                    return str(path)

    # On Windows, check common Docker Desktop installation paths
    if current_platform == "Windows":
        logger.debug("Checking Windows Docker Desktop paths...")
        common_paths = [
            Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
            / "Docker"
            / "Docker"
            / "resources"
            / "bin"
            / "docker.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Docker"
            / "wsl"
            / "docker.exe",
            Path(os.environ.get("ProgramW6432", "C:\\Program Files"))
            / "Docker"
            / "Docker"
            / "resources"
            / "bin"
            / "docker.exe",
        ]

        for path in common_paths:
            logger.debug(f"Checking path: {path} - exists: {path.exists()}")
            if path.exists():
                logger.debug(f"Found Docker at: {path}")
                _docker_detection_cache["docker_path"] = str(path)
                _docker_detection_done = True
                return str(path)

        # Check if Docker is available via WSL
        logger.debug("Docker Desktop not found, checking WSL...")
        try:
            wsl_available, wsl_version = check_wsl_docker()
            if wsl_available:
                logger.info(f"[CloudDesigner] Using Docker via WSL: {wsl_version}")
                _docker_detection_cache["docker_path"] = "wsl docker"
                _docker_detection_done = True
                return "wsl docker"  # Special marker for WSL Docker
            logger.debug("Docker not found via WSL either")
        except Exception as e:
            logger.exception(f"Error checking WSL Docker: {e}")

    logger.debug("Docker executable not found anywhere")
    _docker_detection_cache["docker_path"] = None
    _docker_detection_done = True
    return None


def get_docker_command() -> list[str]:
    """
    Get the Docker command with proper path handling.

    Returns:
        List containing the docker command (may include full path on Windows,
        or the cached WSL Docker command for WSL Docker on Windows)
    """
    global _wsl_docker_command

    docker_path = find_docker_executable()
    if docker_path:
        # Handle WSL Docker special case - use cached command if available
        if docker_path == "wsl docker":
            if _wsl_docker_command:
                return _wsl_docker_command.copy()
            # Fallback if cache not set (shouldn't happen)
            return ["wsl", "docker"]
        return [docker_path]

    # Fall back to just "docker" and let subprocess handle it
    return ["docker"]


def is_using_wsl_docker() -> bool:
    """Check if we're using Docker via WSL."""
    docker_path = find_docker_executable()
    return docker_path == "wsl docker"


def windows_to_wsl_path(windows_path: Path | str) -> str:
    """
    Convert a Windows path to a WSL path.

    Example: C:\\Users\\name\\folder -> /mnt/c/Users/name/folder
    """
    path_str = str(windows_path)

    # Handle UNC paths or already-unix paths
    if path_str.startswith("/"):
        return path_str

    # Convert drive letter (e.g., C: -> /mnt/c)
    if len(path_str) >= 2 and path_str[1] == ":":
        drive = path_str[0].lower()
        rest = path_str[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"

    # Just convert backslashes
    return path_str.replace("\\", "/")


def get_docker_host_ip() -> str | None:
    """
    Get the IP address that Docker containers can use to reach the host.

    For Docker running in WSL, containers need to use the WSL gateway IP
    instead of 'localhost' to reach services on the Windows host.

    Returns:
        The host IP address, or None if not determinable
    """
    # Check if we're running inside WSL (backend running in WSL)
    if is_wsl():
        try:
            # Get the WSL gateway IP directly
            result = subprocess.run(
                ["ip", "route"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('default via'):
                        # Extract IP from "default via 192.168.x.x dev eth0"
                        parts = line.split()
                        if len(parts) >= 3:
                            gateway_ip = parts[2]
                            logger.info(f"[CloudDesigner] Running in WSL - gateway IP: {gateway_ip}")
                            return gateway_ip
        except Exception as e:
            logger.warning(f"[CloudDesigner] Failed to get WSL gateway IP: {e}")

    # Check if we're on Windows calling WSL Docker
    use_wsl = is_using_wsl_docker()
    if use_wsl:
        try:
            docker_cmd = get_docker_command()
            # Get the default gateway inside WSL (this is the Windows host from WSL's perspective)
            result = subprocess.run(
                docker_cmd[:-1] + ["ip", "route"],  # Remove 'docker' from cmd, add 'ip route'
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                creationflags=CREATION_FLAGS,
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('default via'):
                        # Extract IP from "default via 192.168.x.x dev eth0"
                        parts = line.split()
                        if len(parts) >= 3:
                            gateway_ip = parts[2]
                            logger.info(f"[CloudDesigner] Detected WSL gateway IP: {gateway_ip}")
                            return gateway_ip
        except Exception as e:
            logger.warning(f"[CloudDesigner] Failed to get WSL gateway IP: {e}")

    # For Docker Desktop on Mac/Linux, try host.docker.internal
    return "host.docker.internal"


def translate_localhost_url(url: str) -> str:
    """
    Translate a localhost URL to one that Docker containers can reach.

    When running Docker (especially via WSL), containers cannot reach
    'localhost' on the host. This function replaces localhost with the
    appropriate host IP address.

    Args:
        url: The original URL (e.g., "http://localhost:8088")

    Returns:
        Translated URL (e.g., "http://192.168.48.1:8088") or original if no translation needed
    """
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    host = parsed.hostname or ""

    # Check if this is a localhost URL that needs translation
    if host.lower() in ("localhost", "127.0.0.1", "0.0.0.0"):
        docker_host = get_docker_host_ip()
        if docker_host:
            # Reconstruct URL with new host
            # Handle port preservation
            if parsed.port:
                new_netloc = f"{docker_host}:{parsed.port}"
            else:
                new_netloc = docker_host

            new_url = urlunparse((
                parsed.scheme,
                new_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            logger.info(f"[CloudDesigner] Translated URL: {url} -> {new_url}")
            return new_url

    return url


def get_docker_files_path() -> Path:
    """
    Get the path to the Docker files directory.

    Handles both development mode (source files) and bundled mode (PyInstaller).
    """
    # Check if running from PyInstaller bundle
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running from PyInstaller bundle
        base_path = Path(sys._MEIPASS)
        return base_path / "clouddesigner" / "docker_files"
    else:
        # Running from source
        return Path(__file__).parent / "docker_files"

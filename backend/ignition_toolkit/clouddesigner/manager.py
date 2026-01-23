"""
CloudDesigner Manager - Container lifecycle management

Manages the Docker Compose stack for browser-accessible Ignition Designer.
"""

import logging
import os
import platform
import shutil
import sys
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Windows-specific subprocess flag to hide console window
# On non-Windows platforms, use 0 (no flags)
_CREATION_FLAGS = (
    subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
)


def _is_wsl() -> bool:
    """
    Check if running inside Windows Subsystem for Linux (WSL).

    Returns:
        True if running in WSL, False otherwise
    """
    if platform.system() != "Linux":
        return False

    try:
        with open("/proc/version", "r") as f:
            version_info = f.read().lower()
            return "microsoft" in version_info or "wsl" in version_info
    except (FileNotFoundError, PermissionError):
        return False


def _check_wsl_docker() -> bool:
    """
    Check if Docker is available inside WSL (for Windows with WSL2 backend).

    Returns:
        True if Docker is available via WSL, False otherwise
    """
    if platform.system() != "Windows":
        return False

    try:
        result = subprocess.run(
            ["wsl", "docker", "--version"],
            capture_output=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            logger.info("Docker found via WSL")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        logger.debug(f"WSL Docker check failed: {e}")

    return False


def _find_docker_executable() -> str | None:
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
    # First, try to find docker in PATH
    docker_path = shutil.which("docker")
    if docker_path:
        return docker_path

    # On Linux (including WSL), check standard Linux paths
    if platform.system() == "Linux":
        linux_paths = [
            Path("/usr/bin/docker"),
            Path("/usr/local/bin/docker"),
            Path("/snap/bin/docker"),
        ]

        for path in linux_paths:
            if path.exists():
                logger.info(f"Found Docker at: {path}")
                return str(path)

        # If running in WSL, also check Windows Docker Desktop paths via /mnt/c
        if _is_wsl():
            wsl_windows_paths = [
                Path("/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"),
                Path("/mnt/c/Program Files/Docker/Docker/resources/bin/docker"),
            ]

            for path in wsl_windows_paths:
                if path.exists():
                    logger.info(f"Found Docker (WSL Windows) at: {path}")
                    return str(path)

    # On Windows, check common Docker Desktop installation paths
    if platform.system() == "Windows":
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
            if path.exists():
                logger.info(f"Found Docker at: {path}")
                return str(path)

        # Check if Docker is available via WSL
        if _check_wsl_docker():
            return "wsl docker"  # Special marker for WSL Docker

    return None


def _get_docker_command() -> list[str]:
    """
    Get the Docker command with proper path handling.

    Returns:
        List containing the docker command (may include full path on Windows,
        or ["wsl", "docker"] for WSL Docker on Windows)
    """
    docker_path = _find_docker_executable()
    if docker_path:
        # Handle WSL Docker special case
        if docker_path == "wsl docker":
            return ["wsl", "docker"]
        return [docker_path]

    # Fall back to just "docker" and let subprocess handle it
    return ["docker"]


def _get_docker_files_path() -> Path:
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

ContainerStatus = Literal["running", "exited", "paused", "not_created", "unknown"]


@dataclass
class DockerStatus:
    """Docker daemon status"""

    installed: bool
    running: bool
    version: str | None = None
    docker_path: str | None = None


@dataclass
class CloudDesignerStatus:
    """CloudDesigner container status"""

    status: ContainerStatus
    port: int | None = None
    error: str | None = None


class CloudDesignerManager:
    """
    Manages the CloudDesigner Docker stack.

    The stack includes:
    - designer-desktop: Ubuntu desktop with Ignition Designer
    - guacamole: Web-based remote desktop gateway
    - guacd: Guacamole daemon for protocol handling
    - nginx: Reverse proxy (optional)
    """

    CONTAINER_NAME = "clouddesigner-desktop"
    DEFAULT_PORT = 8080

    def __init__(self):
        self.compose_dir = _get_docker_files_path()

    def check_docker_installed(self) -> bool:
        """Check if docker command is available."""
        try:
            docker_cmd = _get_docker_command()
            result = subprocess.run(
                docker_cmd + ["--version"],
                capture_output=True,
                timeout=10,  # Increased timeout for WSL startup
                creationflags=_CREATION_FLAGS,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Docker not found: {e}")
            return False

    def check_docker_running(self) -> bool:
        """Check if Docker daemon is running."""
        try:
            docker_cmd = _get_docker_command()
            result = subprocess.run(
                docker_cmd + ["info"],
                capture_output=True,
                timeout=30,  # Increased timeout for WSL2 startup
                creationflags=_CREATION_FLAGS,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Docker daemon not running: {e}")
            return False

    def get_docker_version(self) -> str | None:
        """Get Docker version string."""
        try:
            docker_cmd = _get_docker_command()
            result = subprocess.run(
                docker_cmd + ["--version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=_CREATION_FLAGS,
            )
            if result.returncode == 0:
                # Parse "Docker version 24.0.7, build afdd53b"
                return result.stdout.strip()
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Could not get Docker version: {e}")
            return None

    def get_docker_status(self) -> DockerStatus:
        """Get comprehensive Docker status."""
        docker_path = _find_docker_executable()
        installed = self.check_docker_installed()
        running = self.check_docker_running() if installed else False
        version = self.get_docker_version() if installed else None

        return DockerStatus(
            installed=installed,
            running=running,
            version=version,
            docker_path=docker_path,
        )

    def get_container_status(self) -> CloudDesignerStatus:
        """Check clouddesigner-desktop container status."""
        try:
            docker_cmd = _get_docker_command()
            result = subprocess.run(
                docker_cmd
                + [
                    "inspect",
                    "-f",
                    "{{.State.Status}}",
                    self.CONTAINER_NAME,
                ],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=_CREATION_FLAGS,
            )

            if result.returncode != 0:
                # Container doesn't exist
                return CloudDesignerStatus(status="not_created")

            status = result.stdout.strip().lower()

            # Map Docker status to our status type
            if status == "running":
                return CloudDesignerStatus(status="running", port=self.DEFAULT_PORT)
            elif status == "exited":
                return CloudDesignerStatus(status="exited")
            elif status == "paused":
                return CloudDesignerStatus(status="paused")
            else:
                return CloudDesignerStatus(status="unknown")

        except FileNotFoundError:
            return CloudDesignerStatus(
                status="not_created",
                error="Docker not found",
            )
        except subprocess.TimeoutExpired:
            return CloudDesignerStatus(
                status="unknown",
                error="Docker command timed out",
            )
        except Exception as e:
            return CloudDesignerStatus(
                status="unknown",
                error=str(e),
            )

    def start(self, gateway_url: str, credential_name: str | None = None) -> dict:
        """
        Start CloudDesigner stack with gateway URL.

        Args:
            gateway_url: The Ignition gateway URL to connect to
            credential_name: Optional credential name for auto-login

        Returns:
            dict with success status and output/error
        """
        if not self.compose_dir.exists():
            return {
                "success": False,
                "error": f"Docker compose directory not found: {self.compose_dir}",
            }

        # Prepare environment
        env = os.environ.copy()
        env["IGNITION_GATEWAY_URL"] = gateway_url
        if credential_name:
            env["IGNITION_CREDENTIAL_NAME"] = credential_name

        try:
            logger.info(f"Starting CloudDesigner stack with gateway: {gateway_url}")
            docker_cmd = _get_docker_command()

            result = subprocess.run(
                docker_cmd + ["compose", "up", "-d"],
                cwd=self.compose_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout for pulling images
                creationflags=_CREATION_FLAGS,
            )

            if result.returncode == 0:
                logger.info("CloudDesigner stack started successfully")
                return {
                    "success": True,
                    "output": result.stdout,
                }
            else:
                logger.error(f"Failed to start CloudDesigner: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr or "Unknown error",
                    "output": result.stdout,
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Docker compose command timed out (may still be pulling images)",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Docker not found. Please install Docker Desktop.",
            }
        except Exception as e:
            logger.exception("Error starting CloudDesigner")
            return {
                "success": False,
                "error": str(e),
            }

    def stop(self) -> dict:
        """
        Stop CloudDesigner stack.

        Returns:
            dict with success status and output/error
        """
        if not self.compose_dir.exists():
            return {
                "success": False,
                "error": f"Docker compose directory not found: {self.compose_dir}",
            }

        try:
            logger.info("Stopping CloudDesigner stack")
            docker_cmd = _get_docker_command()

            result = subprocess.run(
                docker_cmd + ["compose", "down"],
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=_CREATION_FLAGS,
            )

            if result.returncode == 0:
                logger.info("CloudDesigner stack stopped successfully")
                return {
                    "success": True,
                    "output": result.stdout,
                }
            else:
                logger.error(f"Failed to stop CloudDesigner: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr or "Unknown error",
                    "output": result.stdout,
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Docker compose command timed out",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Docker not found",
            }
        except Exception as e:
            logger.exception("Error stopping CloudDesigner")
            return {
                "success": False,
                "error": str(e),
            }

    def get_config(self) -> dict:
        """
        Get current CloudDesigner configuration.

        Returns:
            dict with compose directory and other config info
        """
        return {
            "compose_dir": str(self.compose_dir),
            "compose_dir_exists": self.compose_dir.exists(),
            "container_name": self.CONTAINER_NAME,
            "default_port": self.DEFAULT_PORT,
        }


# Singleton instance
_manager: CloudDesignerManager | None = None


def get_clouddesigner_manager() -> CloudDesignerManager:
    """Get or create the CloudDesigner manager singleton."""
    global _manager
    if _manager is None:
        _manager = CloudDesignerManager()
    return _manager

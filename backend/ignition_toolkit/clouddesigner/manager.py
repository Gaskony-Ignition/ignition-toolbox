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

from ignition_toolkit.credentials.vault import get_credential_vault

logger = logging.getLogger(__name__)

# Windows-specific subprocess flag to hide console window
# On non-Windows platforms, use 0 (no flags)
_CREATION_FLAGS = (
    subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
)

# Cache for the working WSL Docker command prefix
# This stores the command that successfully found Docker (e.g., ["wsl", "-d", "Ubuntu", "docker"])
_wsl_docker_command: list[str] | None = None


def _is_wsl() -> bool:
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
    except Exception:
        return False


def _check_wsl_docker() -> tuple[bool, str | None]:
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
    logger.info(f"WSL Docker check - Platform: {current_platform}")

    if current_platform != "Windows":
        logger.info("WSL Docker check skipped - not on Windows")
        return False, None

    # First check if wsl.exe exists
    wsl_path = shutil.which("wsl")
    if not wsl_path:
        logger.info("WSL not found in PATH")
        return False, None

    logger.info(f"WSL found at: {wsl_path}")

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
            logger.info(f"Trying WSL Docker: {' '.join(test_cmd)}")
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,  # Longer timeout for WSL startup
                creationflags=_CREATION_FLAGS,
            )
            logger.info(f"WSL Docker result: returncode={result.returncode}, stdout={result.stdout[:100] if result.stdout else ''}, stderr={result.stderr[:100] if result.stderr else ''}")
            if result.returncode == 0:
                version = result.stdout.strip()
                # Extract distro name for logging if using -d flag
                distro = test_cmd[test_cmd.index("-d") + 1] if "-d" in test_cmd else "default"
                logger.info(f"Docker found via WSL ({distro}): {version}")
                # Cache the working command prefix for future use
                _wsl_docker_command = docker_prefix
                logger.info(f"Cached WSL Docker command: {_wsl_docker_command}")
                return True, version
            else:
                logger.info(f"WSL Docker command failed: {result.stderr[:100] if result.stderr else 'no error'}")
        except FileNotFoundError as e:
            logger.info(f"WSL command not found: {e}")
            return False, None
        except subprocess.TimeoutExpired:
            logger.info(f"WSL Docker command timed out: {test_cmd}")
        except OSError as e:
            logger.info(f"WSL Docker check error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error checking WSL Docker: {e}")

    logger.info("All WSL Docker detection methods failed")
    return False, None


def _check_wsl_docker_running() -> bool:
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
            logger.info(f"Checking WSL Docker daemon with cached command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=_CREATION_FLAGS,
            )
            if result.returncode == 0:
                logger.info(f"WSL Docker daemon running via cached command")
                return True
            else:
                logger.info(f"WSL Docker daemon not running: {result.stderr[:100] if result.stderr else 'no error'}")
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
                creationflags=_CREATION_FLAGS,
            )
            if result.returncode == 0:
                logger.info(f"WSL Docker daemon running via: {' '.join(cmd)}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"WSL Docker daemon check failed for {cmd}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error checking WSL Docker daemon for {cmd}: {e}")

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
    current_platform = platform.system()
    logger.info(f"Finding Docker executable - Platform: {current_platform}")

    # First, try to find docker in PATH
    docker_path = shutil.which("docker")
    if docker_path:
        logger.info(f"Docker found in PATH: {docker_path}")
        return docker_path

    logger.info("Docker not found in PATH, checking platform-specific locations")

    # On Linux (including WSL), check standard Linux paths
    if current_platform == "Linux":
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
    if current_platform == "Windows":
        logger.info("Checking Windows Docker Desktop paths...")
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
            logger.info(f"Checking path: {path} - exists: {path.exists()}")
            if path.exists():
                logger.info(f"Found Docker at: {path}")
                return str(path)

        # Check if Docker is available via WSL
        logger.info("Docker Desktop not found, checking WSL...")
        try:
            wsl_available, wsl_version = _check_wsl_docker()
            if wsl_available:
                logger.info(f"Using Docker via WSL: {wsl_version}")
                return "wsl docker"  # Special marker for WSL Docker
            logger.info("Docker not found via WSL either")
        except Exception as e:
            logger.exception(f"Error checking WSL Docker: {e}")

    logger.info("Docker executable not found anywhere")
    return None


def _get_docker_command() -> list[str]:
    """
    Get the Docker command with proper path handling.

    Returns:
        List containing the docker command (may include full path on Windows,
        or the cached WSL Docker command for WSL Docker on Windows)
    """
    global _wsl_docker_command

    docker_path = _find_docker_executable()
    if docker_path:
        # Handle WSL Docker special case - use cached command if available
        if docker_path == "wsl docker":
            if _wsl_docker_command:
                logger.info(f"Using cached WSL Docker command: {_wsl_docker_command}")
                return _wsl_docker_command.copy()
            # Fallback if cache not set (shouldn't happen)
            return ["wsl", "docker"]
        return [docker_path]

    # Fall back to just "docker" and let subprocess handle it
    return ["docker"]


def _is_using_wsl_docker() -> bool:
    """Check if we're using Docker via WSL."""
    docker_path = _find_docker_executable()
    return docker_path == "wsl docker"


def _windows_to_wsl_path(windows_path: Path | str) -> str:
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


def _quote_wsl_path(path: str) -> str:
    """
    Quote a path for use in WSL shell commands if it contains spaces.

    When running subprocess with WSL, the shell inside WSL re-interprets
    arguments, so paths with spaces need to be quoted.

    Example: /mnt/c/Program Files/path -> '/mnt/c/Program Files/path'
    """
    if " " in path:
        # Use single quotes to prevent shell expansion
        # Escape any existing single quotes in the path
        escaped = path.replace("'", "'\\''")
        return f"'{escaped}'"
    return path


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
            logger.debug(f"Checking Docker installed with command: {docker_cmd}")
            result = subprocess.run(
                docker_cmd + ["--version"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,  # Longer timeout for WSL startup
                creationflags=_CREATION_FLAGS,
            )
            if result.returncode == 0:
                logger.info(f"Docker installed: {result.stdout.strip()}")
                return True
            else:
                logger.debug(f"Docker check failed: {result.stderr}")
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Docker not found: {e}")
            return False

    def check_docker_running(self) -> bool:
        """Check if Docker daemon is running."""
        try:
            docker_cmd = _get_docker_command()
            logger.debug(f"Checking Docker running with command: {docker_cmd}")
            result = subprocess.run(
                docker_cmd + ["info"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=45,  # Longer timeout for WSL2 startup
                creationflags=_CREATION_FLAGS,
            )
            if result.returncode == 0:
                logger.info("Docker daemon is running")
                return True
            else:
                logger.debug(f"Docker daemon not running: {result.stderr}")
                return False
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
                encoding='utf-8',
                errors='replace',
                timeout=30,  # Longer timeout for WSL
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
        logger.info("Checking Docker status...")
        docker_path = _find_docker_executable()
        logger.info(f"Docker path: {docker_path}")

        installed = self.check_docker_installed()
        logger.info(f"Docker installed: {installed}")

        running = self.check_docker_running() if installed else False
        logger.info(f"Docker running: {running}")

        version = self.get_docker_version() if installed else None

        # Provide user-friendly path info
        display_path = docker_path
        if docker_path == "wsl docker":
            display_path = "WSL (Windows Subsystem for Linux)"

        return DockerStatus(
            installed=installed,
            running=running,
            version=version,
            docker_path=display_path,
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
                encoding='utf-8',
                errors='replace',
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
            logger.error(f"[CloudDesigner] Docker compose directory not found: {self.compose_dir}")
            return {
                "success": False,
                "error": f"Docker compose directory not found: {self.compose_dir}",
            }

        # Prepare environment
        env = os.environ.copy()
        env["IGNITION_GATEWAY_URL"] = gateway_url

        # Fetch credentials from vault if credential_name is provided
        if credential_name:
            env["IGNITION_CREDENTIAL_NAME"] = credential_name
            try:
                vault = get_credential_vault()
                logger.info(f"[CloudDesigner] Looking up credential '{credential_name}' from vault")

                credential = vault.get_credential(credential_name)
                if credential:
                    env["IGNITION_USERNAME"] = credential.username
                    env["IGNITION_PASSWORD"] = credential.password
                    logger.info(f"[CloudDesigner] ✓ Loaded credentials for '{credential_name}' (user: {credential.username})")
                else:
                    logger.warning(f"[CloudDesigner] ✗ Credential '{credential_name}' not found in vault")
            except Exception as e:
                logger.exception(f"[CloudDesigner] Failed to load credentials: {e}")

        try:
            logger.info(f"[CloudDesigner] ========================================")
            logger.info(f"[CloudDesigner] Starting CloudDesigner with gateway: {gateway_url}")
            logger.info(f"[CloudDesigner] ========================================")

            docker_cmd = _get_docker_command()
            logger.info(f"[CloudDesigner] Using docker command: {' '.join(docker_cmd)}")

            # Determine if we need WSL path conversion
            use_wsl = _is_using_wsl_docker()
            compose_file = self.compose_dir / "docker-compose.yml"

            if use_wsl:
                wsl_compose_file = _windows_to_wsl_path(compose_file)
                # Quote the path for WSL shell (spaces in "Program Files" etc.)
                quoted_compose_file = _quote_wsl_path(wsl_compose_file)
                compose_args = ["compose", "-f", quoted_compose_file]
                run_cwd = None
                logger.info(f"[CloudDesigner] Using WSL compose file: {quoted_compose_file}")
            else:
                compose_args = ["compose"]
                run_cwd = self.compose_dir
                logger.info(f"[CloudDesigner] Using compose directory: {run_cwd}")

            # Step 1: Clean up
            logger.info("[CloudDesigner] ----------------------------------------")
            logger.info("[CloudDesigner] STEP 1/4: Cleaning up existing containers...")
            logger.info("[CloudDesigner] ----------------------------------------")
            cleanup_result = subprocess.run(
                docker_cmd + compose_args + ["down", "-v"],
                cwd=run_cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
                creationflags=_CREATION_FLAGS,
            )
            if cleanup_result.returncode != 0:
                logger.warning(f"[CloudDesigner] Cleanup warning (continuing): {cleanup_result.stderr[:200] if cleanup_result.stderr else 'none'}")
            else:
                logger.info("[CloudDesigner] ✓ Step 1 complete: Cleanup successful")

            # Step 2: Remove cached guacamole image
            logger.info("[CloudDesigner] ----------------------------------------")
            logger.info("[CloudDesigner] STEP 2/4: Removing cached guacamole image...")
            logger.info("[CloudDesigner] ----------------------------------------")
            rmi_result = subprocess.run(
                docker_cmd + ["rmi", "guacamole/guacamole:1.5.4"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=_CREATION_FLAGS,
            )
            if rmi_result.returncode != 0:
                logger.info("[CloudDesigner] ✓ Step 2 complete: No cached image (this is OK)")
            else:
                logger.info("[CloudDesigner] ✓ Step 2 complete: Guacamole image removed")

            # Step 3: Build designer-desktop image
            logger.info("[CloudDesigner] ----------------------------------------")
            logger.info("[CloudDesigner] STEP 3/4: Building designer-desktop image...")
            logger.info("[CloudDesigner] This may take 5-10 minutes on first run!")
            logger.info("[CloudDesigner] ----------------------------------------")

            # Use Popen to stream build output for better visibility
            build_cmd = docker_cmd + compose_args + ["build", "--no-cache", "--progress=plain", "designer-desktop"]
            logger.info(f"[CloudDesigner] Running: {' '.join(build_cmd)}")

            build_process = subprocess.Popen(
                build_cmd,
                cwd=run_cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=_CREATION_FLAGS,
            )

            # Stream build output to logs
            build_output_lines = []
            try:
                for line in iter(build_process.stdout.readline, ''):
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        build_output_lines.append(line)
                        # Log significant build steps
                        if any(keyword in line.lower() for keyword in ['step', 'run ', 'copy ', 'downloading', 'extracting', 'installing', 'error', 'warning']):
                            # Truncate long lines
                            log_line = line[:150] + '...' if len(line) > 150 else line
                            logger.info(f"[CloudDesigner Build] {log_line}")

                build_process.wait(timeout=600)  # 10 minute timeout
            except subprocess.TimeoutExpired:
                build_process.kill()
                logger.error("[CloudDesigner] Build timed out after 10 minutes")
                return {
                    "success": False,
                    "error": "Docker build timed out after 10 minutes. Try running 'docker system prune' to free up space.",
                    "output": "\n".join(build_output_lines[-50:]),  # Last 50 lines
                }

            if build_process.returncode != 0:
                error_output = "\n".join(build_output_lines[-20:])  # Last 20 lines
                logger.error(f"[CloudDesigner] Build failed with code {build_process.returncode}")
                logger.error(f"[CloudDesigner] Build output (last 20 lines):\n{error_output}")
                return {
                    "success": False,
                    "error": f"Docker build failed (exit code {build_process.returncode}). Check logs for details.",
                    "output": error_output,
                }
            logger.info("[CloudDesigner] ✓ Step 3 complete: Image built successfully")

            # Step 4: Start containers
            logger.info("[CloudDesigner] ----------------------------------------")
            logger.info("[CloudDesigner] STEP 4/4: Starting containers...")
            logger.info("[CloudDesigner] ----------------------------------------")

            result = subprocess.run(
                docker_cmd + compose_args + ["up", "-d"],
                cwd=run_cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,
                creationflags=_CREATION_FLAGS,
            )

            if result.returncode == 0:
                logger.info("[CloudDesigner] ✓ Step 4 complete: Containers started")
                logger.info("[CloudDesigner] ========================================")
                logger.info("[CloudDesigner] SUCCESS! CloudDesigner is starting up")
                logger.info("[CloudDesigner] Access at: http://localhost:8080")
                logger.info("[CloudDesigner] ========================================")

                # Wait a moment and check container health
                import time
                time.sleep(3)
                container_status = self.get_container_status()
                logger.info(f"[CloudDesigner] Container status after startup: {container_status.status}")

                return {
                    "success": True,
                    "output": result.stdout,
                }
            else:
                logger.error(f"[CloudDesigner] Failed to start containers: {result.stderr}")
                # Try to get container logs for debugging
                try:
                    logs_result = subprocess.run(
                        docker_cmd + compose_args + ["logs", "--tail=50"],
                        cwd=run_cwd,
                        env=env,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=30,
                        creationflags=_CREATION_FLAGS,
                    )
                    if logs_result.stdout:
                        logger.error(f"[CloudDesigner] Container logs:\n{logs_result.stdout}")
                except Exception:
                    pass

                return {
                    "success": False,
                    "error": result.stderr or "Unknown error starting containers",
                    "output": result.stdout,
                }

        except subprocess.TimeoutExpired as e:
            logger.error(f"[CloudDesigner] Timeout during startup: {e}")
            return {
                "success": False,
                "error": "Docker operation timed out. The operation may still be in progress - check 'docker ps' or try again.",
            }
        except FileNotFoundError as e:
            logger.error(f"[CloudDesigner] Docker not found: {e}")
            return {
                "success": False,
                "error": "Docker not found. Please install Docker Desktop.",
            }
        except Exception as e:
            logger.exception(f"[CloudDesigner] Unexpected error during startup: {e}")
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

            # Handle WSL path conversion
            use_wsl = _is_using_wsl_docker()
            compose_file = self.compose_dir / "docker-compose.yml"

            if use_wsl:
                wsl_compose_file = _windows_to_wsl_path(compose_file)
                # Quote the path for WSL shell (spaces in "Program Files" etc.)
                quoted_compose_file = _quote_wsl_path(wsl_compose_file)
                compose_args = ["compose", "-f", quoted_compose_file]
                run_cwd = None
            else:
                compose_args = ["compose"]
                run_cwd = self.compose_dir

            result = subprocess.run(
                docker_cmd + compose_args + ["down"],
                cwd=run_cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
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

    def cleanup(self) -> dict:
        """
        Forcefully clean up all CloudDesigner containers, volumes, and images.

        This is useful when containers get into a bad state or there are conflicts.

        Returns:
            dict with success status and details of cleanup operations
        """
        if not self.compose_dir.exists():
            return {
                "success": False,
                "error": f"Docker compose directory not found: {self.compose_dir}",
            }

        cleanup_results = []
        docker_cmd = _get_docker_command()

        # Handle WSL path conversion
        use_wsl = _is_using_wsl_docker()
        compose_file = self.compose_dir / "docker-compose.yml"

        if use_wsl:
            wsl_compose_file = _windows_to_wsl_path(compose_file)
            # Quote the path for WSL shell (spaces in "Program Files" etc.)
            quoted_compose_file = _quote_wsl_path(wsl_compose_file)
            compose_args = ["compose", "-f", quoted_compose_file]
            run_cwd = None
        else:
            compose_args = ["compose"]
            run_cwd = self.compose_dir

        try:
            logger.info("[CloudDesigner Cleanup] Starting thorough cleanup...")

            # Step 1: docker compose down -v --remove-orphans
            logger.info("[CloudDesigner Cleanup] Step 1/5: Stopping and removing containers and volumes...")
            result = subprocess.run(
                docker_cmd + compose_args + ["down", "-v", "--remove-orphans"],
                cwd=run_cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120,
                creationflags=_CREATION_FLAGS,
            )
            cleanup_results.append(f"compose down: {'OK' if result.returncode == 0 else result.stderr[:100]}")

            # Step 2: Force remove any lingering clouddesigner containers
            logger.info("[CloudDesigner Cleanup] Step 2/5: Force removing any lingering containers...")
            container_names = [
                "clouddesigner-desktop",
                "clouddesigner-guacamole",
                "clouddesigner-guacd",
                "clouddesigner-nginx",
            ]
            for container in container_names:
                result = subprocess.run(
                    docker_cmd + ["rm", "-f", container],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=30,
                    creationflags=_CREATION_FLAGS,
                )
                if result.returncode == 0:
                    cleanup_results.append(f"rm {container}: removed")

            # Step 3: Remove clouddesigner network if it exists
            logger.info("[CloudDesigner Cleanup] Step 3/5: Removing network...")
            result = subprocess.run(
                docker_cmd + ["network", "rm", "docker_files_clouddesigner-net"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=_CREATION_FLAGS,
            )
            if result.returncode == 0:
                cleanup_results.append("network: removed")

            # Step 4: Remove clouddesigner volumes
            logger.info("[CloudDesigner Cleanup] Step 4/5: Removing volumes...")
            volume_names = [
                "docker_files_designer-home",
                "docker_files_shared-workspace",
                "docker_files_guacd-drive",
            ]
            for volume in volume_names:
                result = subprocess.run(
                    docker_cmd + ["volume", "rm", "-f", volume],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=30,
                    creationflags=_CREATION_FLAGS,
                )
                if result.returncode == 0:
                    cleanup_results.append(f"volume {volume}: removed")

            # Step 5: Optionally remove cached images
            logger.info("[CloudDesigner Cleanup] Step 5/5: Removing cached images...")
            images_to_remove = [
                "docker_files-designer-desktop",
                "guacamole/guacamole:1.5.4",
                "guacamole/guacd:1.5.4",
                "nginx:alpine",  # Standard nginx image used by the stack
            ]
            for image in images_to_remove:
                result = subprocess.run(
                    docker_cmd + ["rmi", "-f", image],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=60,
                    creationflags=_CREATION_FLAGS,
                )
                if result.returncode == 0:
                    cleanup_results.append(f"image {image}: removed")

            logger.info(f"[CloudDesigner Cleanup] Cleanup complete: {cleanup_results}")
            return {
                "success": True,
                "output": "\n".join(cleanup_results),
            }

        except subprocess.TimeoutExpired as e:
            logger.error(f"[CloudDesigner Cleanup] Timeout: {e}")
            return {
                "success": False,
                "error": "Cleanup operation timed out",
                "output": "\n".join(cleanup_results),
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Docker not found",
            }
        except Exception as e:
            logger.exception("[CloudDesigner Cleanup] Error during cleanup")
            return {
                "success": False,
                "error": str(e),
                "output": "\n".join(cleanup_results),
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

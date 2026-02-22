"""
Stack Runner - Deploy and manage Docker Compose stacks locally

Manages the lifecycle of StackBuilder-generated Docker Compose stacks
on the local Docker environment.
"""

import logging
import os
import platform
import shutil
import subprocess
import tempfile
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
    """
    if platform.system() != "Linux":
        return False

    try:
        with open("/proc/version") as f:
            version_info = f.read().lower()
            return "microsoft" in version_info or "wsl" in version_info
    except (FileNotFoundError, PermissionError):
        return False


def _find_docker_executable() -> str | None:
    """
    Find the Docker executable path.
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

    return None


def _get_docker_command() -> list[str]:
    """Get the Docker command with proper path handling."""
    docker_path = _find_docker_executable()
    if docker_path:
        return [docker_path]
    return ["docker"]


StackStatus = Literal["running", "partial", "stopped", "not_deployed", "unknown"]


@dataclass
class DeployedStackStatus:
    """Status of a deployed stack"""

    status: StackStatus
    services: dict[str, str]  # service_name -> status
    error: str | None = None


@dataclass
class DeployResult:
    """Result of a deploy operation"""

    success: bool
    output: str | None = None
    error: str | None = None


class StackRunner:
    """
    Manages Docker Compose stacks for local deployment.

    Handles:
    - Deploying stacks from generated compose content
    - Stopping running stacks
    - Checking stack status
    """

    # Directory to store deployed stacks
    STACKS_DIR = Path(tempfile.gettempdir()) / "ignition-toolbox-stacks"

    def __init__(self):
        # Ensure stacks directory exists
        self.STACKS_DIR.mkdir(parents=True, exist_ok=True)

    def _get_stack_dir(self, stack_name: str) -> Path:
        """Get the directory path for a specific stack."""
        return self.STACKS_DIR / stack_name

    def check_docker_available(self) -> bool:
        """Check if Docker is available and running."""
        try:
            docker_cmd = _get_docker_command()
            result = subprocess.run(
                docker_cmd + ["info"],
                capture_output=True,
                timeout=30,
                creationflags=_CREATION_FLAGS,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Docker not available: {e}")
            return False

    def deploy_stack(
        self,
        stack_name: str,
        compose_content: str,
        env_content: str = "",
        config_files: dict[str, str] | None = None,
    ) -> DeployResult:
        """
        Deploy a Docker Compose stack.

        Args:
            stack_name: Name for the stack (used as project name)
            compose_content: Content of docker-compose.yml
            env_content: Content of .env file
            config_files: Additional config files {path: content}

        Returns:
            DeployResult with success status and output/error
        """
        if not self.check_docker_available():
            return DeployResult(
                success=False,
                error="Docker is not available. Please ensure Docker is installed and running.",
            )

        # Create stack directory
        stack_dir = self._get_stack_dir(stack_name)
        stack_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Write compose file
            compose_path = stack_dir / "docker-compose.yml"
            compose_path.write_text(compose_content, encoding='utf-8')

            # Write env file
            if env_content:
                env_path = stack_dir / ".env"
                env_path.write_text(env_content, encoding='utf-8')

            # Write additional config files
            if config_files:
                for file_path, content in config_files.items():
                    full_path = stack_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding='utf-8')

            # Run docker compose up
            logger.info(f"Deploying stack '{stack_name}' from {stack_dir}")
            docker_cmd = _get_docker_command()

            result = subprocess.run(
                docker_cmd + ["compose", "-p", stack_name, "up", "-d"],
                cwd=stack_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,  # 5 minute timeout for pulling images
                creationflags=_CREATION_FLAGS,
            )

            if result.returncode == 0:
                logger.info(f"Stack '{stack_name}' deployed successfully")
                return DeployResult(
                    success=True,
                    output=result.stdout or result.stderr,
                )
            else:
                logger.error(f"Failed to deploy stack: {result.stderr}")
                return DeployResult(
                    success=False,
                    error=result.stderr or "Unknown error",
                    output=result.stdout,
                )

        except subprocess.TimeoutExpired:
            return DeployResult(
                success=False,
                error="Docker compose command timed out. Images may still be pulling in the background.",
            )
        except FileNotFoundError:
            return DeployResult(
                success=False,
                error="Docker not found. Please install Docker.",
            )
        except Exception as e:
            logger.exception(f"Error deploying stack: {e}")
            return DeployResult(
                success=False,
                error=str(e),
            )

    def stop_stack(self, stack_name: str, remove_volumes: bool = False) -> DeployResult:
        """
        Stop a running stack.

        Args:
            stack_name: Name of the stack to stop
            remove_volumes: If True, also remove volumes

        Returns:
            DeployResult with success status and output/error
        """
        stack_dir = self._get_stack_dir(stack_name)

        if not stack_dir.exists():
            return DeployResult(
                success=False,
                error=f"Stack '{stack_name}' directory not found.",
            )

        try:
            logger.info(f"Stopping stack '{stack_name}'")
            docker_cmd = _get_docker_command()

            cmd = docker_cmd + ["compose", "-p", stack_name, "down"]
            if remove_volumes:
                cmd.append("-v")

            result = subprocess.run(
                cmd,
                cwd=stack_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120,
                creationflags=_CREATION_FLAGS,
            )

            if result.returncode == 0:
                logger.info(f"Stack '{stack_name}' stopped successfully")
                return DeployResult(
                    success=True,
                    output=result.stdout or result.stderr,
                )
            else:
                logger.error(f"Failed to stop stack: {result.stderr}")
                return DeployResult(
                    success=False,
                    error=result.stderr or "Unknown error",
                    output=result.stdout,
                )

        except subprocess.TimeoutExpired:
            return DeployResult(
                success=False,
                error="Docker compose command timed out.",
            )
        except FileNotFoundError:
            return DeployResult(
                success=False,
                error="Docker not found.",
            )
        except Exception as e:
            logger.exception(f"Error stopping stack: {e}")
            return DeployResult(
                success=False,
                error=str(e),
            )

    def get_stack_status(self, stack_name: str) -> DeployedStackStatus:
        """
        Get the status of a deployed stack.

        Args:
            stack_name: Name of the stack to check

        Returns:
            DeployedStackStatus with container states
        """
        stack_dir = self._get_stack_dir(stack_name)

        if not stack_dir.exists():
            return DeployedStackStatus(
                status="not_deployed",
                services={},
            )

        try:
            docker_cmd = _get_docker_command()

            # Get container status using docker compose ps
            result = subprocess.run(
                docker_cmd + ["compose", "-p", stack_name, "ps", "--format", "json"],
                cwd=stack_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=_CREATION_FLAGS,
            )

            if result.returncode != 0:
                # No containers found
                return DeployedStackStatus(
                    status="not_deployed",
                    services={},
                )

            # Parse JSON output (one JSON object per line)
            import json

            services = {}
            running_count = 0
            total_count = 0

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    container = json.loads(line)
                    service_name = container.get("Service", container.get("Name", "unknown"))
                    state = container.get("State", "unknown").lower()
                    services[service_name] = state
                    total_count += 1
                    if state == "running":
                        running_count += 1
                except json.JSONDecodeError:
                    continue

            if total_count == 0:
                return DeployedStackStatus(
                    status="not_deployed",
                    services={},
                )
            elif running_count == total_count:
                return DeployedStackStatus(
                    status="running",
                    services=services,
                )
            elif running_count == 0:
                return DeployedStackStatus(
                    status="stopped",
                    services=services,
                )
            else:
                return DeployedStackStatus(
                    status="partial",
                    services=services,
                )

        except subprocess.TimeoutExpired:
            return DeployedStackStatus(
                status="unknown",
                services={},
                error="Docker command timed out",
            )
        except Exception as e:
            logger.exception(f"Error getting stack status: {e}")
            return DeployedStackStatus(
                status="unknown",
                services={},
                error=str(e),
            )

    def list_deployed_stacks(self) -> list[str]:
        """List all deployed stack names."""
        if not self.STACKS_DIR.exists():
            return []
        return [d.name for d in self.STACKS_DIR.iterdir() if d.is_dir()]

    def delete_stack(self, stack_name: str) -> DeployResult:
        """
        Delete a stack directory (after stopping).

        Args:
            stack_name: Name of the stack to delete

        Returns:
            DeployResult with success status
        """
        stack_dir = self._get_stack_dir(stack_name)

        if not stack_dir.exists():
            return DeployResult(
                success=True,
                output="Stack directory already deleted.",
            )

        try:
            # First try to stop if running
            self.stop_stack(stack_name, remove_volumes=True)

            # Remove directory
            shutil.rmtree(stack_dir)
            logger.info(f"Stack '{stack_name}' directory deleted")
            return DeployResult(
                success=True,
                output="Stack deleted successfully.",
            )
        except Exception as e:
            logger.exception(f"Error deleting stack: {e}")
            return DeployResult(
                success=False,
                error=str(e),
            )


# Singleton instance
_runner: StackRunner | None = None


def get_stack_runner() -> StackRunner:
    """Get or create the StackRunner singleton."""
    global _runner
    if _runner is None:
        _runner = StackRunner()
    return _runner

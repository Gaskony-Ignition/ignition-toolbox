"""
CloudDesigner Manager - Container lifecycle management

Manages the Docker Compose stack for browser-accessible Ignition Designer.
"""

import logging
import os
import subprocess
import time
from pathlib import Path

from ignition_toolkit.clouddesigner.docker import (
    CREATION_FLAGS,
    find_docker_executable,
    get_docker_command,
    get_docker_files_path,
    is_using_wsl_docker,
    translate_localhost_url,
    windows_to_wsl_path,
)
from ignition_toolkit.clouddesigner.models import (
    CloudDesignerStatus,
    DockerStatus,
)
from ignition_toolkit.core.paths import get_data_dir
from ignition_toolkit.credentials.vault import get_credential_vault

logger = logging.getLogger(__name__)


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
    ALL_CONTAINER_NAMES = [
        "clouddesigner-desktop",
        "clouddesigner-guacamole",
        "clouddesigner-guacd",
        "clouddesigner-nginx",
    ]
    DEFAULT_PORT = 8080

    def __init__(self):
        self.compose_dir = get_docker_files_path()
        # Write .env to writable data dir, not the (possibly read-only) install dir
        self._env_file = get_data_dir() / "clouddesigner" / ".env"

    def _get_compose_args(self) -> tuple[list[str], "Path"]:
        """
        Get docker compose arguments and working directory.

        Uses cwd-based approach for both WSL and native Docker.
        Docker Compose finds docker-compose.yml in the working directory.
        The .env file is passed explicitly via --env-file since it lives
        in the writable data directory (not the install directory).

        For WSL, this avoids path-quoting issues when paths contain spaces
        (e.g., /mnt/c/Program Files/...). The cwd is set at the OS process level
        and doesn't go through shell argument parsing.

        Returns:
            Tuple of (compose_args, run_cwd)
        """
        args = ["compose"]
        if self._env_file.exists():
            env_path = str(self._env_file)
            if is_using_wsl_docker():
                env_path = windows_to_wsl_path(env_path)
            args += ["--env-file", env_path]
        return args, self.compose_dir

    def _write_compose_env(self, env_vars: dict[str, str]) -> None:
        """
        Write a .env file for Docker Compose in the compose directory.

        This is the reliable way to pass environment variables to Docker Compose,
        especially when running through WSL where Windows env vars are NOT
        automatically forwarded to the Linux environment.

        Docker Compose automatically reads .env from the project directory.

        Args:
            env_vars: Dictionary of environment variable names to values
        """
        # Write to the writable data directory, not the install directory
        self._env_file.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for key, value in env_vars.items():
            if value is None:
                continue
            # Docker Compose .env format: KEY=VALUE
            # Quote values containing spaces, quotes, or special characters
            if any(c in value for c in ' "\'\n\\$#'):
                escaped = value.replace('\\', '\\\\').replace('"', '\\"')
                lines.append(f'{key}="{escaped}"')
            else:
                lines.append(f'{key}={value}')

        self._env_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        # Log var names but not values (may contain passwords)
        logger.info(f"[CloudDesigner] Wrote .env file to {self._env_file} with variables: {list(env_vars.keys())}")

    def _image_exists(self, image_name: str) -> bool:
        """Check if a Docker image exists locally."""
        try:
            docker_cmd = get_docker_command()
            result = subprocess.run(
                docker_cmd + ["image", "inspect", image_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=15,
                creationflags=CREATION_FLAGS,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _all_containers_running(self) -> bool:
        """Check if all CloudDesigner containers are running."""
        try:
            docker_cmd = get_docker_command()
            for name in self.ALL_CONTAINER_NAMES:
                result = subprocess.run(
                    docker_cmd + ["inspect", "-f", "{{.State.Status}}", name],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=10,
                    creationflags=CREATION_FLAGS,
                )
                if result.returncode != 0 or result.stdout.strip().lower() != "running":
                    return False
            return True
        except Exception:
            return False

    # ==========================================================================
    # Image Management (Stage 1 & 2)
    # ==========================================================================

    REQUIRED_IMAGES = {
        "nginx:alpine": "pull",
        "guacamole/guacd:1.5.4": "pull",
        "guacamole/guacamole:1.5.4": "pull",
        "clouddesigner-desktop": "build",
    }

    def get_image_status(self) -> dict:
        """
        Check which required Docker images are available locally.

        Returns:
            dict with per-image status and overall readiness
        """
        images = {}
        all_ready = True

        for image_name, source in self.REQUIRED_IMAGES.items():
            exists = self._image_exists(image_name)
            images[image_name] = {
                "exists": exists,
                "source": source,  # "pull" or "build"
            }
            if not exists:
                all_ready = False

        return {
            "images": images,
            "all_ready": all_ready,
        }

    def pull_images(self) -> dict:
        """
        Pull required base images (nginx, guacamole).

        Returns:
            dict with success status and details
        """
        docker_cmd = get_docker_command()
        pull_results = []

        images_to_pull = [name for name, src in self.REQUIRED_IMAGES.items() if src == "pull"]

        for image_name in images_to_pull:
            if self._image_exists(image_name):
                pull_results.append(f"{image_name}: already exists")
                logger.info(f"[CloudDesigner] Image {image_name} already exists, skipping pull")
                continue

            logger.info(f"[CloudDesigner] Pulling {image_name}...")
            try:
                result = subprocess.run(
                    docker_cmd + ["pull", image_name],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=300,
                    creationflags=CREATION_FLAGS,
                )
                if result.returncode == 0:
                    pull_results.append(f"{image_name}: pulled")
                    logger.info(f"[CloudDesigner] Pulled {image_name}")
                else:
                    pull_results.append(f"{image_name}: FAILED - {result.stderr[:100]}")
                    logger.error(f"[CloudDesigner] Failed to pull {image_name}: {result.stderr}")
                    return {
                        "success": False,
                        "error": f"Failed to pull {image_name}: {result.stderr[:200]}",
                        "output": "\n".join(pull_results),
                    }
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": f"Timed out pulling {image_name}",
                    "output": "\n".join(pull_results),
                }

        return {
            "success": True,
            "output": "\n".join(pull_results),
        }

    def build_desktop_image(self, force: bool = False) -> dict:
        """
        Build the designer-desktop Docker image.

        Args:
            force: If True, rebuilds even if image exists

        Returns:
            dict with success status and output/error
        """
        if not force and self._image_exists("clouddesigner-desktop"):
            logger.info("[CloudDesigner] designer-desktop image already exists, skipping build")
            return {
                "success": True,
                "output": "Image already exists (use force=true to rebuild)",
            }

        if not self.compose_dir.exists():
            return {
                "success": False,
                "error": f"Docker compose directory not found: {self.compose_dir}",
            }

        logger.info(f"[CloudDesigner] Building designer-desktop image (force={force})...")

        docker_cmd = get_docker_command()
        compose_args, run_cwd = self._get_compose_args()
        env = os.environ.copy()

        return self._build_image(docker_cmd, compose_args, run_cwd, env)

    def check_docker_installed(self) -> bool:
        """Check if docker command is available."""
        try:
            docker_cmd = get_docker_command()
            logger.debug(f"Checking Docker installed with command: {docker_cmd}")
            result = subprocess.run(
                docker_cmd + ["--version"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,  # Longer timeout for WSL startup
                creationflags=CREATION_FLAGS,
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
            docker_cmd = get_docker_command()
            logger.debug(f"Checking Docker running with command: {docker_cmd}")
            result = subprocess.run(
                docker_cmd + ["info"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=45,  # Longer timeout for WSL2 startup
                creationflags=CREATION_FLAGS,
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
            docker_cmd = get_docker_command()
            result = subprocess.run(
                docker_cmd + ["--version"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,  # Longer timeout for WSL
                creationflags=CREATION_FLAGS,
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
        logger.debug("Checking Docker status...")
        docker_path = find_docker_executable()
        logger.debug(f"Docker path: {docker_path}")

        installed = self.check_docker_installed()
        logger.debug(f"Docker installed: {installed}")

        running = self.check_docker_running() if installed else False
        logger.debug(f"Docker running: {running}")

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

    def get_all_container_statuses(self) -> dict[str, str]:
        """
        Get status of all CloudDesigner containers.

        Returns:
            dict mapping container name to status string
            (e.g., {"clouddesigner-desktop": "running", "clouddesigner-nginx": "running"})
        """
        docker_cmd = get_docker_command()
        statuses = {}
        for name in self.ALL_CONTAINER_NAMES:
            try:
                result = subprocess.run(
                    docker_cmd + ["inspect", "-f", "{{.State.Status}}", name],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=10,
                    creationflags=CREATION_FLAGS,
                )
                if result.returncode == 0:
                    statuses[name] = result.stdout.strip().lower()
                else:
                    statuses[name] = "not_found"
            except subprocess.TimeoutExpired:
                statuses[name] = "timeout"
            except Exception:
                statuses[name] = "error"
        return statuses

    def get_container_status(self) -> CloudDesignerStatus:
        """Check clouddesigner-desktop container status."""
        try:
            docker_cmd = get_docker_command()
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
                creationflags=CREATION_FLAGS,
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
            elif status == "restarting":
                return CloudDesignerStatus(
                    status="restarting",
                    error="Container is crash-looping. Check Docker logs for details.",
                )
            elif status == "created":
                return CloudDesignerStatus(
                    status="created",
                    error="Container was created but hasn't started yet.",
                )
            else:
                return CloudDesignerStatus(
                    status="unknown",
                    error=f"Unexpected container state: {status}",
                )

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

    def _build_image(self, docker_cmd: list[str], compose_args: list[str],
                      run_cwd: str | None, env: dict) -> dict:
        """
        Build the designer-desktop Docker image with streaming output.

        Returns:
            dict with success status and output/error
        """
        import queue
        import threading

        build_cmd = docker_cmd + compose_args + ["build", "--progress=plain", "designer-desktop"]
        logger.info(f"[CloudDesigner] Running: {' '.join(build_cmd)}")

        build_process = subprocess.Popen(
            build_cmd,
            cwd=run_cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            creationflags=CREATION_FLAGS,
        )

        build_output_lines: list[str] = []
        output_queue: queue.Queue[str | None] = queue.Queue()

        def read_output(pipe, q):
            """Read output from pipe in a separate thread to avoid blocking."""
            try:
                while True:
                    chunk = pipe.read(1024)
                    if not chunk:
                        break
                    try:
                        text = chunk.decode('utf-8', errors='replace')
                        q.put(text)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"[CloudDesigner] Output reader error: {e}")
            finally:
                q.put(None)

        reader_thread = threading.Thread(
            target=read_output,
            args=(build_process.stdout, output_queue),
            daemon=True
        )
        reader_thread.start()

        build_timeout = 1800  # 30 minutes
        start_time = time.time()
        last_progress_log = start_time
        last_output_time = start_time
        partial_line = ""
        lines_received = 0
        saw_build_completion = False

        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed > build_timeout:
                    build_process.kill()
                    logger.error("[CloudDesigner] Build timed out after 30 minutes")
                    return {
                        "success": False,
                        "error": "Docker build timed out after 30 minutes. Try running 'docker system prune' to free up space.",
                        "output": "\n".join(build_output_lines[-50:]),
                    }

                ret = build_process.poll()
                if ret is not None:
                    logger.info(f"[CloudDesigner] Build process finished with code {ret}, draining output...")
                    while True:
                        try:
                            chunk = output_queue.get_nowait()
                            if chunk is None:
                                break
                            partial_line += chunk
                        except queue.Empty:
                            break
                    if partial_line.strip():
                        build_output_lines.append(partial_line.strip())
                    break

                time_since_last_output = time.time() - last_output_time
                if saw_build_completion and time_since_last_output > 60:
                    logger.info(f"[CloudDesigner] Build appears complete (no output for {int(time_since_last_output)}s after completion indicators)")
                    try:
                        build_process.terminate()
                        build_process.wait(timeout=10)
                    except Exception:
                        build_process.kill()
                    break

                try:
                    chunk = output_queue.get(timeout=5.0)
                    if chunk is None:
                        break
                    partial_line += chunk
                    last_output_time = time.time()

                    while '\n' in partial_line:
                        line, partial_line = partial_line.split('\n', 1)
                        line = line.strip()
                        if line:
                            build_output_lines.append(line)
                            lines_received += 1
                            line_lower = line.lower()
                            if any(indicator in line_lower for indicator in [
                                'exporting to image',
                                'naming to docker.io',
                                'successfully built',
                                'successfully tagged',
                            ]):
                                saw_build_completion = True
                            if any(keyword in line.lower() for keyword in ['step', 'run ', 'copy ', 'downloading', 'extracting', 'installing', 'error', 'warning', '#']):
                                log_line = line[:150] + '...' if len(line) > 150 else line
                                logger.info(f"[CloudDesigner Build] {log_line}")
                except queue.Empty:
                    now = time.time()
                    if now - last_progress_log >= 30:
                        minutes = int(elapsed // 60)
                        seconds = int(elapsed % 60)
                        completion_hint = " (build appears complete, waiting for process)" if saw_build_completion else ""
                        logger.info(f"[CloudDesigner] Build in progress... ({minutes}m {seconds}s elapsed, {lines_received} lines received){completion_hint}")
                        last_progress_log = now
                    continue

            try:
                build_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                build_process.kill()
                build_process.wait(timeout=10)
            logger.info(f"[CloudDesigner] Build complete. Total lines: {lines_received}, return code: {build_process.returncode}")
        except subprocess.TimeoutExpired:
            build_process.kill()
            logger.error("[CloudDesigner] Build process did not terminate cleanly")
            return {
                "success": False,
                "error": "Docker build did not terminate cleanly.",
                "output": "\n".join(build_output_lines[-50:]),
            }

        if build_process.returncode != 0 and not saw_build_completion:
            error_output = "\n".join(build_output_lines[-20:])
            logger.error(f"[CloudDesigner] Build failed with code {build_process.returncode}")
            logger.error(f"[CloudDesigner] Build output (last 20 lines):\n{error_output}")
            return {
                "success": False,
                "error": f"Docker build failed (exit code {build_process.returncode}). Check logs for details.",
                "output": error_output,
            }
        elif build_process.returncode != 0 and saw_build_completion:
            logger.warning(f"[CloudDesigner] Build returned code {build_process.returncode} but completion indicators were seen - treating as success")

        return {"success": True, "output": "\n".join(build_output_lines[-10:])}

    def start(self, gateway_url: str, credential_name: str | None = None,
              force_rebuild: bool = False) -> dict:
        """
        Start CloudDesigner stack with gateway URL.

        Uses smart caching: if the designer-desktop image already exists and
        containers are not in a bad state, skips the full rebuild and just
        starts containers. This reduces startup from ~20 minutes to seconds
        on subsequent starts.

        Args:
            gateway_url: The Ignition gateway URL to connect to
            credential_name: Optional credential name for auto-login
            force_rebuild: If True, forces a full image rebuild

        Returns:
            dict with success status and output/error
        """
        logger.info("[CloudDesigner] ===== MANAGER START CALLED =====")
        logger.info(f"[CloudDesigner] Gateway URL: {gateway_url}")
        logger.info(f"[CloudDesigner] Credential: {credential_name}")
        logger.info(f"[CloudDesigner] Force rebuild: {force_rebuild}")
        logger.info(f"[CloudDesigner] Compose dir: {self.compose_dir}")
        logger.info(f"[CloudDesigner] Compose dir exists: {self.compose_dir.exists()}")
        logger.info(f"[CloudDesigner] Using WSL Docker: {is_using_wsl_docker()}")

        if not self.compose_dir.exists():
            logger.error(f"[CloudDesigner] Docker compose directory not found: {self.compose_dir}")
            return {
                "success": False,
                "error": f"Docker compose directory not found: {self.compose_dir}",
            }

        # Validate required subdirectories exist (critical for production builds)
        required_dirs = ["nginx", "guacamole", "designer-desktop"]
        required_files = ["docker-compose.yml", "designer-desktop/Dockerfile"]

        for subdir in required_dirs:
            subdir_path = self.compose_dir / subdir
            if not subdir_path.exists():
                logger.error(f"[CloudDesigner] Required directory not found: {subdir_path}")
                return {
                    "success": False,
                    "error": f"Required Docker directory not found: {subdir}. This may indicate a packaging issue.",
                }

        for file in required_files:
            file_path = self.compose_dir / file
            if not file_path.exists():
                logger.error(f"[CloudDesigner] Required file not found: {file_path}")
                return {
                    "success": False,
                    "error": f"Required Docker file not found: {file}. This may indicate a packaging issue.",
                }

        logger.info("[CloudDesigner] All required docker files validated successfully")

        # Prepare environment
        env = os.environ.copy()

        # Translate localhost URLs for Docker container connectivity
        docker_gateway_url = translate_localhost_url(gateway_url)
        env["IGNITION_GATEWAY_URL"] = docker_gateway_url

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
                    logger.info(f"[CloudDesigner] Loaded credentials for '{credential_name}' (user: {credential.username})")
                else:
                    logger.warning(f"[CloudDesigner] Credential '{credential_name}' not found in vault")
            except Exception as e:
                logger.exception(f"[CloudDesigner] Failed to load credentials: {e}")

        # Write .env file for Docker Compose
        # This ensures env vars reach Docker Compose even when running through WSL,
        # where Windows environment variables are not automatically forwarded.
        compose_env: dict[str, str] = {
            "IGNITION_GATEWAY_URL": docker_gateway_url,
        }
        if env.get("IGNITION_USERNAME"):
            compose_env["IGNITION_USERNAME"] = env["IGNITION_USERNAME"]
        if env.get("IGNITION_PASSWORD"):
            compose_env["IGNITION_PASSWORD"] = env["IGNITION_PASSWORD"]
        try:
            self._write_compose_env(compose_env)
        except OSError as e:
            logger.error(f"[CloudDesigner] Failed to write .env file: {e}")
            return {
                "success": False,
                "error": f"Failed to write Docker Compose environment file: {e}",
            }

        try:
            logger.info("[CloudDesigner] ========================================")
            logger.info(f"[CloudDesigner] Starting CloudDesigner with gateway: {gateway_url}")
            logger.info("[CloudDesigner] ========================================")

            docker_cmd = get_docker_command()
            logger.info(f"[CloudDesigner] Using docker command: {' '.join(docker_cmd)}")

            compose_args, run_cwd = self._get_compose_args()

            # Check current state to determine what we need to do
            image_exists = self._image_exists("clouddesigner-desktop")
            containers_running = self._all_containers_running()

            logger.info(f"[CloudDesigner] Image exists: {image_exists}")
            logger.info(f"[CloudDesigner] Containers running: {containers_running}")

            # Fast path: if containers are already running and no rebuild needed,
            # just recreate them with updated environment (new gateway/credentials)
            if containers_running and not force_rebuild:
                logger.info("[CloudDesigner] Containers already running - restarting with updated config")
                # Stop existing containers (without removing volumes)
                subprocess.run(
                    docker_cmd + compose_args + ["down"],
                    cwd=run_cwd,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=60,
                    creationflags=CREATION_FLAGS,
                )
                # Start with new environment
                result = subprocess.run(
                    docker_cmd + compose_args + ["up", "-d"],
                    cwd=run_cwd,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=300,
                    creationflags=CREATION_FLAGS,
                )
                if result.returncode == 0:
                    logger.info("[CloudDesigner] Containers restarted with updated config")
                    time.sleep(3)
                    return {"success": True, "output": "Restarted with updated configuration"}
                else:
                    logger.warning(f"[CloudDesigner] Restart failed, falling through to full start: {result.stderr}")

            # If image exists and we're not forcing rebuild, skip the build step
            needs_build = force_rebuild or not image_exists
            if needs_build:
                step_count = 3
            else:
                step_count = 2
            current_step = 0

            # Step: Stop any existing containers (without destroying volumes)
            current_step += 1
            logger.info("[CloudDesigner] ----------------------------------------")
            logger.info(f"[CloudDesigner] STEP {current_step}/{step_count}: Stopping existing containers...")
            logger.info("[CloudDesigner] ----------------------------------------")
            cleanup_result = subprocess.run(
                docker_cmd + compose_args + ["down"],
                cwd=run_cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
                creationflags=CREATION_FLAGS,
            )
            if cleanup_result.returncode != 0:
                stderr = cleanup_result.stderr or ""
                if "no configuration file" in stderr.lower() or "not found" in stderr.lower():
                    logger.error(f"[CloudDesigner] CRITICAL: Docker compose file not accessible: {stderr[:300]}")
                    return {
                        "success": False,
                        "error": "Docker compose configuration not found. This may be a path or permission issue.",
                        "output": stderr,
                    }
                logger.warning(f"[CloudDesigner] Cleanup warning (continuing): {stderr[:200] if stderr else 'none'}")
            else:
                logger.info(f"[CloudDesigner] Step {current_step} complete: Cleanup successful")

            # Step: Build image (only if needed)
            if needs_build:
                current_step += 1
                logger.info("[CloudDesigner] ----------------------------------------")
                logger.info(f"[CloudDesigner] STEP {current_step}/{step_count}: Building designer-desktop image...")
                if not image_exists:
                    logger.info("[CloudDesigner] First build - this may take 10-20 minutes!")
                else:
                    logger.info(f"[CloudDesigner] Rebuilding image (force_rebuild={force_rebuild})...")
                logger.info("[CloudDesigner] ----------------------------------------")

                build_result = self._build_image(docker_cmd, compose_args, run_cwd, env)
                if not build_result["success"]:
                    return build_result
                logger.info(f"[CloudDesigner] Step {current_step} complete: Image built successfully")
            else:
                logger.info("[CloudDesigner] Skipping build - image already exists (use cleanup + start to force rebuild)")

            # Step: Start containers
            current_step += 1
            logger.info("[CloudDesigner] ----------------------------------------")
            logger.info(f"[CloudDesigner] STEP {current_step}/{step_count}: Starting containers...")
            logger.info("[CloudDesigner] ----------------------------------------")

            up_cmd = docker_cmd + compose_args + ["up", "-d"]
            logger.info(f"[CloudDesigner] Running: {' '.join(up_cmd)} (cwd={run_cwd})")

            result = subprocess.run(
                up_cmd,
                cwd=run_cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,
                creationflags=CREATION_FLAGS,
            )

            logger.info(f"[CloudDesigner] compose up returned code {result.returncode}")
            if result.stdout:
                logger.info(f"[CloudDesigner] compose up stdout: {result.stdout[:500]}")
            if result.stderr:
                logger.info(f"[CloudDesigner] compose up stderr: {result.stderr[:500]}")

            if result.returncode == 0:
                logger.info(f"[CloudDesigner] Step {current_step} complete: Containers started")
                logger.info("[CloudDesigner] ========================================")
                logger.info("[CloudDesigner] SUCCESS! CloudDesigner is starting up")
                logger.info("[CloudDesigner] Access at: http://localhost:8080")
                logger.info("[CloudDesigner] ========================================")

                # Wait for containers to initialize, then check all container statuses
                time.sleep(5)
                all_statuses = self.get_all_container_statuses()
                logger.info(f"[CloudDesigner] All container statuses after startup: {all_statuses}")

                container_status = self.get_container_status()
                logger.info(f"[CloudDesigner] Primary container status: {container_status.status}")

                # Check if any container failed to start
                failed_containers = {
                    name: status for name, status in all_statuses.items()
                    if status not in ("running",)
                }

                if container_status.status != "running" or failed_containers:
                    # Log which containers failed
                    for name, status in failed_containers.items():
                        logger.warning(f"[CloudDesigner] Container {name} is not running (status: {status})")

                    # Fetch compose logs for diagnosis
                    try:
                        logs_result = subprocess.run(
                            docker_cmd + compose_args + ["logs", "--tail=30"],
                            cwd=run_cwd,
                            env=env,
                            capture_output=True,
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            timeout=15,
                            creationflags=CREATION_FLAGS,
                        )
                        if logs_result.stdout:
                            logger.warning(f"[CloudDesigner] Container logs:\n{logs_result.stdout[-1500:]}")
                        if logs_result.stderr:
                            logger.warning(f"[CloudDesigner] Container stderr:\n{logs_result.stderr[-500:]}")
                    except Exception as log_error:
                        logger.warning(f"[CloudDesigner] Could not fetch container logs: {log_error}")

                    if container_status.status != "running":
                        # Primary container failed — report failure
                        status_summary = ", ".join(f"{n.replace('clouddesigner-', '')}: {s}" for n, s in all_statuses.items())
                        return {
                            "success": False,
                            "error": f"Containers failed to reach running state. Status: {status_summary}",
                            "output": result.stdout,
                        }
                    else:
                        # Primary is running but some auxiliary containers failed — warn but continue
                        logger.warning("[CloudDesigner] Primary container running but some auxiliary containers failed")

                return {
                    "success": True,
                    "output": result.stdout,
                }
            else:
                logger.error(f"[CloudDesigner] Failed to start containers: {result.stderr}")
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
                        creationflags=CREATION_FLAGS,
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
        Stop CloudDesigner stack (preserves images and volumes for fast restart).

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
            docker_cmd = get_docker_command()
            compose_args, run_cwd = self._get_compose_args()

            result = subprocess.run(
                docker_cmd + compose_args + ["down"],
                cwd=run_cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
                creationflags=CREATION_FLAGS,
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

        This is the nuclear option - removes everything so the next start
        will do a full rebuild. Use when containers are in a bad state.

        Returns:
            dict with success status and details of cleanup operations
        """
        if not self.compose_dir.exists():
            return {
                "success": False,
                "error": f"Docker compose directory not found: {self.compose_dir}",
            }

        cleanup_results = []
        docker_cmd = get_docker_command()
        compose_args, run_cwd = self._get_compose_args()

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
                creationflags=CREATION_FLAGS,
            )
            cleanup_results.append(f"compose down: {'OK' if result.returncode == 0 else result.stderr[:100]}")

            # Step 2: Force remove any lingering clouddesigner containers
            logger.info("[CloudDesigner Cleanup] Step 2/5: Force removing any lingering containers...")
            for container in self.ALL_CONTAINER_NAMES:
                result = subprocess.run(
                    docker_cmd + ["rm", "-f", container],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=30,
                    creationflags=CREATION_FLAGS,
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
                creationflags=CREATION_FLAGS,
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
                    creationflags=CREATION_FLAGS,
                )
                if result.returncode == 0:
                    cleanup_results.append(f"volume {volume}: removed")

            # Step 5: Remove cached images
            logger.info("[CloudDesigner Cleanup] Step 5/5: Removing cached images...")
            images_to_remove = [
                "clouddesigner-desktop",
                "guacamole/guacamole:1.5.4",
                "guacamole/guacd:1.5.4",
                "nginx:alpine",
            ]
            for image in images_to_remove:
                result = subprocess.run(
                    docker_cmd + ["rmi", "-f", image],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=60,
                    creationflags=CREATION_FLAGS,
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

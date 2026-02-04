"""
CloudDesigner Manager - Container lifecycle management

Manages the Docker Compose stack for browser-accessible Ignition Designer.
"""

import logging
import os
import subprocess
import time

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
    DEFAULT_PORT = 8080

    def __init__(self):
        self.compose_dir = get_docker_files_path()

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
        logger.info("Checking Docker status...")
        docker_path = find_docker_executable()
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
        logger.info(f"[CloudDesigner] ===== MANAGER START CALLED =====")
        logger.info(f"[CloudDesigner] Gateway URL: {gateway_url}")
        logger.info(f"[CloudDesigner] Credential: {credential_name}")
        logger.info(f"[CloudDesigner] Compose dir: {self.compose_dir}")
        logger.info(f"[CloudDesigner] Compose dir exists: {self.compose_dir.exists()}")

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

        logger.info(f"[CloudDesigner] All required docker files validated successfully")

        # Prepare environment
        env = os.environ.copy()

        # Translate localhost URLs for Docker container connectivity
        # Containers can't reach 'localhost' on the host, need to use host IP
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

        try:
            logger.info(f"[CloudDesigner] ========================================")
            logger.info(f"[CloudDesigner] Starting CloudDesigner with gateway: {gateway_url}")
            logger.info(f"[CloudDesigner] ========================================")

            docker_cmd = get_docker_command()
            logger.info(f"[CloudDesigner] Using docker command: {' '.join(docker_cmd)}")

            # Determine if we need WSL path conversion
            use_wsl = is_using_wsl_docker()
            compose_file = self.compose_dir / "docker-compose.yml"

            if use_wsl:
                wsl_compose_file = windows_to_wsl_path(compose_file)
                wsl_compose_dir = windows_to_wsl_path(self.compose_dir)
                # Note: Do NOT quote the path - subprocess passes arguments directly
                # without shell interpretation, so quotes become literal characters
                # CRITICAL: Use --project-directory to tell docker-compose where to resolve
                # relative paths (./nginx, ./guacamole, etc.) from. Without this, relative
                # paths in docker-compose.yml fail because cwd is unpredictable in production.
                compose_args = ["compose", "-f", wsl_compose_file, "--project-directory", wsl_compose_dir]
                run_cwd = None
                logger.info(f"[CloudDesigner] Using WSL compose file: {wsl_compose_file}")
                logger.info(f"[CloudDesigner] Using WSL project directory: {wsl_compose_dir}")
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
                creationflags=CREATION_FLAGS,
            )
            if cleanup_result.returncode != 0:
                stderr = cleanup_result.stderr or ""
                # Check for critical errors that indicate the compose file can't be found
                if "no configuration file" in stderr.lower() or "not found" in stderr.lower():
                    logger.error(f"[CloudDesigner] CRITICAL: Docker compose file not accessible: {stderr[:300]}")
                    return {
                        "success": False,
                        "error": f"Docker compose configuration not found. This may be a path or permission issue.",
                        "output": stderr,
                    }
                # Non-critical cleanup warnings (e.g., no containers to remove) - continue
                logger.warning(f"[CloudDesigner] Cleanup warning (continuing): {stderr[:200] if stderr else 'none'}")
            else:
                logger.info("[CloudDesigner] Step 1 complete: Cleanup successful")

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
                creationflags=CREATION_FLAGS,
            )
            if rmi_result.returncode != 0:
                logger.info("[CloudDesigner] Step 2 complete: No cached image (this is OK)")
            else:
                logger.info("[CloudDesigner] Step 2 complete: Guacamole image removed")

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
                bufsize=1,  # Line buffered - critical for proper output streaming
                creationflags=CREATION_FLAGS,
            )

            # Stream build output to logs using thread-based reading to avoid blocking
            # This fixes silent failures in production where readline() can block indefinitely
            import queue
            import threading

            build_output_lines: list[str] = []
            output_queue: queue.Queue[str | None] = queue.Queue()

            def read_output(pipe, q):
                """Read output from pipe in a separate thread to avoid blocking."""
                try:
                    while True:
                        # Read raw bytes and decode - more reliable than text mode
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
                    q.put(None)  # Signal end of output

            reader_thread = threading.Thread(
                target=read_output,
                args=(build_process.stdout, output_queue),
                daemon=True
            )
            reader_thread.start()

            # Process output with timeout handling
            build_timeout = 600  # 10 minutes
            start_time = time.time()
            last_progress_log = start_time
            partial_line = ""
            lines_received = 0

            try:
                while True:
                    elapsed = time.time() - start_time
                    if elapsed > build_timeout:
                        build_process.kill()
                        logger.error("[CloudDesigner] Build timed out after 10 minutes")
                        return {
                            "success": False,
                            "error": "Docker build timed out after 10 minutes. Try running 'docker system prune' to free up space.",
                            "output": "\n".join(build_output_lines[-50:]),
                        }

                    # Check if process has finished
                    ret = build_process.poll()
                    if ret is not None:
                        # Process finished, drain remaining output
                        logger.info(f"[CloudDesigner] Build process finished with code {ret}, draining output...")
                        while True:
                            try:
                                chunk = output_queue.get_nowait()
                                if chunk is None:
                                    break
                                partial_line += chunk
                            except queue.Empty:
                                break
                        # Process any remaining partial line
                        if partial_line.strip():
                            build_output_lines.append(partial_line.strip())
                        break

                    # Get output with timeout (don't block forever)
                    try:
                        chunk = output_queue.get(timeout=5.0)
                        if chunk is None:
                            break  # End of output
                        partial_line += chunk

                        # Process complete lines
                        while '\n' in partial_line:
                            line, partial_line = partial_line.split('\n', 1)
                            line = line.strip()
                            if line:
                                build_output_lines.append(line)
                                lines_received += 1
                                # Log significant build steps
                                if any(keyword in line.lower() for keyword in ['step', 'run ', 'copy ', 'downloading', 'extracting', 'installing', 'error', 'warning', '#']):
                                    log_line = line[:150] + '...' if len(line) > 150 else line
                                    logger.info(f"[CloudDesigner Build] {log_line}")
                    except queue.Empty:
                        # No output for 5 seconds, but process still running
                        # Log progress every 30 seconds so user knows build is ongoing
                        now = time.time()
                        if now - last_progress_log >= 30:
                            minutes = int(elapsed // 60)
                            seconds = int(elapsed % 60)
                            logger.info(f"[CloudDesigner] Build in progress... ({minutes}m {seconds}s elapsed, {lines_received} lines received)")
                            last_progress_log = now
                        continue

                # Wait for process to fully complete
                build_process.wait(timeout=30)
                logger.info(f"[CloudDesigner] Build complete. Total lines: {lines_received}")
            except subprocess.TimeoutExpired:
                build_process.kill()
                logger.error("[CloudDesigner] Build process did not terminate cleanly")
                return {
                    "success": False,
                    "error": "Docker build did not terminate cleanly.",
                    "output": "\n".join(build_output_lines[-50:]),
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
            logger.info("[CloudDesigner] Step 3 complete: Image built successfully")

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
                creationflags=CREATION_FLAGS,
            )

            if result.returncode == 0:
                logger.info("[CloudDesigner] Step 4 complete: Containers started")
                logger.info("[CloudDesigner] ========================================")
                logger.info("[CloudDesigner] SUCCESS! CloudDesigner is starting up")
                logger.info("[CloudDesigner] Access at: http://localhost:8080")
                logger.info("[CloudDesigner] ========================================")

                # Wait a moment and check container health
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
            docker_cmd = get_docker_command()

            # Handle WSL path conversion
            use_wsl = is_using_wsl_docker()
            compose_file = self.compose_dir / "docker-compose.yml"

            if use_wsl:
                wsl_compose_file = windows_to_wsl_path(compose_file)
                # Note: Do NOT quote the path - subprocess passes arguments directly
                # without shell interpretation, so quotes become literal characters
                compose_args = ["compose", "-f", wsl_compose_file]
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
        docker_cmd = get_docker_command()

        # Handle WSL path conversion
        use_wsl = is_using_wsl_docker()
        compose_file = self.compose_dir / "docker-compose.yml"

        if use_wsl:
            wsl_compose_file = windows_to_wsl_path(compose_file)
            # Note: Do NOT quote the path - subprocess passes arguments directly
            # without shell interpretation, so quotes become literal characters
            compose_args = ["compose", "-f", wsl_compose_file]
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
                creationflags=CREATION_FLAGS,
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

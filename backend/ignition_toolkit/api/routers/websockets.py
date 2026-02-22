"""
WebSocket endpoints router

Handles real-time updates for playbook executions and Claude Code PTY sessions.
Note: PTY terminal sessions are only available on Unix systems.
"""

import asyncio
import logging
import os
import shutil
import signal
import subprocess
import sys
from datetime import datetime

# PTY modules are Unix-only - import conditionally
IS_WINDOWS = sys.platform == "win32"
if not IS_WINDOWS:
    import pty
    import select
    import termios
    import tty

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ignition_toolkit.core.paths import get_playbooks_dir
from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.playbook.models import ExecutionState

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])


# Dependency injection functions to access global state
def get_websocket_connections() -> list[WebSocket]:
    """Get shared websocket connections list from app"""
    from ignition_toolkit.api.app import websocket_connections

    return websocket_connections


def get_active_engines() -> dict[str, "PlaybookEngine"]:
    """Get shared active engines dict from app"""
    from ignition_toolkit.api.routers.executions.helpers import get_active_engines as _get_active_engines

    return _get_active_engines()


def get_claude_code_processes() -> dict[str, subprocess.Popen]:
    """Get shared claude code processes dict from app"""
    from ignition_toolkit.api.app import claude_code_processes

    return claude_code_processes


# ============================================================================
# WebSocket Endpoints
# ============================================================================


@router.websocket("/ws/executions")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for real-time execution updates with heartbeat support

    SECURITY WARNING: Uses API key authentication. Set WEBSOCKET_API_KEY
    environment variable in production. Default key is for development only.
    """
    import hmac

    # Simple authentication: check for API key in query params
    api_key = websocket.query_params.get("api_key")
    from ignition_toolkit.core.config import get_settings
    expected_key = get_settings().websocket_api_key

    # SECURITY: Use constant-time comparison to prevent timing attacks
    if not api_key or not hmac.compare_digest(api_key, expected_key):
        logger.warning(f"Unauthorized WebSocket connection attempt from {websocket.client}")
        await websocket.close(code=1008, reason="Unauthorized")
        return

    # Get WebSocketManager from app state
    from starlette.requests import Request
    from fastapi import Request as FastAPIRequest

    # Access app through websocket's scope
    app = websocket.app
    websocket_manager = app.state.services.websocket_manager

    # Use WebSocketManager's connect method
    await websocket_manager.connect(websocket)
    logger.info(f"WebSocket connection accepted from {websocket.client}")

    try:
        while True:
            # Keep connection alive and handle heartbeat
            data = await websocket.receive_text()

            # Parse message to check for ping/pong
            try:
                import json

                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    # Respond to client-initiated heartbeat ping
                    await websocket.send_json(
                        {"type": "pong", "timestamp": message.get("timestamp")}
                    )
                    logger.debug("Client heartbeat ping received and acknowledged")
                elif msg_type == "pong":
                    # Client responding to our server keepalive - just acknowledge
                    logger.debug("Client acknowledged server keepalive")
                else:
                    # Echo back other messages for compatibility
                    await websocket.send_json({"type": "pong", "data": data})
            except json.JSONDecodeError:
                # Not JSON, echo back as before
                await websocket.send_json({"type": "pong", "data": data})

    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket_manager.disconnect(websocket)


@router.websocket("/ws/claude-code/{execution_id}")
async def claude_code_terminal(websocket: WebSocket, execution_id: str):
    """
    WebSocket endpoint for embedded Claude Code terminal.
    Spawns a Claude Code process with PTY and proxies stdin/stdout.

    Requires API key authentication (same as /ws/executions and /ws/shell).

    Note: This feature requires Unix PTY support and is not available on Windows.
    """
    import hmac

    # Authenticate: check for API key in query params
    api_key = websocket.query_params.get("api_key")
    from ignition_toolkit.core.config import get_settings
    expected_key = get_settings().websocket_api_key

    if not api_key or not hmac.compare_digest(api_key, expected_key):
        logger.warning(f"Unauthorized claude-code WebSocket connection attempt from {websocket.client}")
        await websocket.close(code=1008, reason="Unauthorized")
        return

    logger.info(f"[TERMINAL DEBUG] WebSocket connection request for execution: {execution_id}")
    await websocket.accept()
    logger.info(f"[TERMINAL DEBUG] WebSocket accepted for execution: {execution_id}")

    # PTY terminal sessions are not supported on Windows
    if IS_WINDOWS:
        await websocket.send_json(
            {"type": "error", "message": "Terminal sessions are not supported on Windows"}
        )
        await websocket.close(code=1008, reason="Not supported on Windows")
        return

    master_fd = None
    process = None

    try:
        # Get execution context
        active_engines = get_active_engines()
        engine = active_engines.get(execution_id)
        if not engine:
            await websocket.send_json(
                {"type": "error", "message": "Execution not found or not active"}
            )
            await websocket.close(code=1008, reason="Execution not found")
            return

        execution_state = engine.get_current_execution()
        if not execution_state:
            await websocket.send_json({"type": "error", "message": "Execution state not available"})
            await websocket.close(code=1008, reason="No execution state")
            return

        # Find playbook path
        playbook_name = execution_state.playbook_name
        playbooks_dir = get_playbooks_dir().resolve()
        playbook_path = None

        import yaml

        # Search for playbook by name
        for yaml_file in playbooks_dir.rglob("*.yaml"):
            # Skip backup files
            if ".backup." in yaml_file.name:
                continue
            try:
                with open(yaml_file, encoding='utf-8') as f:
                    playbook_data = yaml.safe_load(f)
                    if playbook_data and playbook_data.get("name") == playbook_name:
                        playbook_path = str(yaml_file.absolute())
                        logger.info(f"Found playbook: {playbook_path}")
                        break
            except Exception as e:
                logger.warning(f"Error reading {yaml_file}: {e}")
                continue

        if not playbook_path:
            error_msg = f"Playbook file not found for '{playbook_name}' in {playbooks_dir}"
            logger.error(error_msg)
            await websocket.send_json({"type": "error", "message": error_msg})
            await websocket.close(code=1008, reason="Playbook not found")
            return

        # Build context message
        context_parts = [
            "# Playbook Execution Debug Session",
            "",
            f"**Execution ID:** {execution_id}",
            f"**Playbook:** {playbook_name}",
            f"**Status:** {execution_state.status.value}",
            f"**Current Step:** {execution_state.current_step_index + 1 if execution_state.current_step_index is not None else 'N/A'}",
            "",
        ]

        # Add step results
        if execution_state.step_results:
            context_parts.append("## Step Results:")
            for idx, result in enumerate(execution_state.step_results, 1):
                status_str = (
                    result.status.value
                    if hasattr(result, "status")
                    else str(result.get("status", "unknown"))
                )
                status_emoji = "✅" if status_str == "success" else "❌"
                step_name = (
                    result.step_name
                    if hasattr(result, "step_name")
                    else result.get("step_name", "Unknown")
                )
                context_parts.append(f"{status_emoji} **Step {idx}:** {step_name}")
                error = result.error if hasattr(result, "error") else result.get("error")
                if error:
                    context_parts.append(f"   Error: {error}")
            context_parts.append("")

        context_message = "\n".join(context_parts)

        # Spawn interactive bash shell in playbook directory with PTY
        master_fd, slave_fd = pty.openpty()

        # Set terminal to raw mode for proper interactivity
        try:
            attrs = termios.tcgetattr(slave_fd)
            attrs[3] = attrs[3] & ~termios.ECHO  # Disable echo (terminal handles it)
            termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)
            tty.setraw(master_fd)  # Set master to raw mode
        except Exception as e:
            logger.warning(f"Could not set PTY to raw mode: {e}")

        # Get playbook directory
        playbook_dir = os.path.dirname(playbook_path)

        # Spawn interactive bash shell
        cmd_args = ["/bin/bash", "-i"]  # -i for interactive mode

        # Set up environment
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"  # Set terminal type
        env["PS1"] = f"\\[\\033[1;32m\\]{playbook_name}\\[\\033[0m\\]:\\[\\033[1;34m\\]\\w\\[\\033[0m\\]$ "

        process = subprocess.Popen(
            cmd_args,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=playbook_dir,  # Start in playbook directory
            env=env,
            preexec_fn=os.setsid,  # Create new process group
            close_fds=True,
        )

        os.close(slave_fd)  # Parent doesn't need slave_fd

        claude_code_processes = get_claude_code_processes()
        claude_code_processes[execution_id] = process

        logger.info(f"Interactive shell started: PID={process.pid}, cwd={playbook_dir}")

        # Send initial welcome message with context
        welcome_msg = (
            f"Terminal session started for {playbook_name}\n"
            f"Working directory: {playbook_dir}\n"
            f"Playbook file: {os.path.basename(playbook_path)}\n"
            f"\n{context_message}\n"
            f"\nYou can now run commands interactively. To launch Claude Code:\n"
            f"  claude-code -p {os.path.basename(playbook_path)}\n"
            f"\n"
        )

        logger.info(f"[TERMINAL DEBUG] Sending welcome message to client, PID: {process.pid}")
        await websocket.send_json(
            {
                "type": "connected",
                "message": welcome_msg,
                "pid": process.pid,
            }
        )
        logger.info(f"[TERMINAL DEBUG] Welcome message sent successfully")

        # Create tasks for bidirectional I/O
        async def read_from_pty():
            """Read output from PTY and send to WebSocket"""
            logger.info(f"[TERMINAL DEBUG] read_from_pty task started")
            while True:
                try:
                    # Check if process is still alive
                    if process.poll() is not None:
                        logger.info(f"[TERMINAL DEBUG] Process exited: {process.pid}")
                        await websocket.send_json({"type": "exit", "code": process.returncode})
                        break

                    # Use select to check if data is available (non-blocking)
                    readable, _, _ = select.select([master_fd], [], [], 0.1)
                    if readable:
                        data = os.read(master_fd, 1024)
                        if not data:
                            logger.info(f"[TERMINAL DEBUG] No data from PTY, breaking")
                            break
                        # Send binary data as bytes WebSocket frame
                        logger.debug(f"[TERMINAL DEBUG] Sending {len(data)} bytes to client")
                        await websocket.send_bytes(data)
                    else:
                        # Small sleep to prevent busy loop
                        await asyncio.sleep(0.01)

                except OSError as e:
                    logger.error(f"[TERMINAL DEBUG] OSError in read_from_pty: {e}")
                    break
                except Exception as e:
                    logger.error(f"[TERMINAL DEBUG] Error reading from PTY: {e}")
                    break
            logger.info(f"[TERMINAL DEBUG] read_from_pty task ended")

        async def write_to_pty():
            """Receive data from WebSocket and write to PTY"""
            logger.info(f"[TERMINAL DEBUG] write_to_pty task started")
            while True:
                try:
                    message = await websocket.receive()
                    logger.debug(f"[TERMINAL DEBUG] Received message from client: {message.keys()}")

                    if "bytes" in message:
                        # Binary data from terminal
                        data = message["bytes"]
                        logger.debug(f"[TERMINAL DEBUG] Writing {len(data)} bytes to PTY")
                        os.write(master_fd, data)
                    elif "text" in message:
                        # Text message (e.g., resize events)
                        import json

                        try:
                            msg = json.loads(message["text"])
                            logger.debug(f"[TERMINAL DEBUG] Text message: {msg.get('type')}")
                            if msg.get("type") == "resize":
                                # Handle terminal resize (optional)
                                pass
                        except json.JSONDecodeError:
                            pass

                except WebSocketDisconnect:
                    logger.info(f"[TERMINAL DEBUG] WebSocket disconnected in write_to_pty")
                    break
                except Exception as e:
                    logger.error(f"[TERMINAL DEBUG] Error writing to PTY: {e}")
                    break
            logger.info(f"[TERMINAL DEBUG] write_to_pty task ended")

        # Run both tasks concurrently
        await asyncio.gather(read_from_pty(), write_to_pty(), return_exceptions=True)

    except Exception as e:
        logger.exception(f"Claude Code WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass  # WebSocket already closed

    finally:
        # Cleanup
        logger.info(f"Cleaning up Claude Code session: {execution_id}")

        if process:
            try:
                # Try graceful termination first
                if process.poll() is None:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Force kill if still running
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        process.wait()
            except Exception as e:
                logger.error(f"Error terminating Claude Code process: {e}")

        if master_fd is not None:
            try:
                os.close(master_fd)
            except Exception:
                pass

        claude_code_processes = get_claude_code_processes()
        if execution_id in claude_code_processes:
            del claude_code_processes[execution_id]

        try:
            await websocket.close()
        except Exception:
            pass



@router.websocket("/ws/shell")
async def shell_terminal(websocket: WebSocket):
    """
    WebSocket endpoint for embedded bash shell terminal.
    Spawns a bash shell with PTY in the specified directory (default: playbooks).

    ⚠️  CRITICAL SECURITY WARNING ⚠️
    This endpoint provides FULL SHELL ACCESS with unrestricted command execution.
    It should ONLY be used in:
    - Development environments
    - Trusted, isolated networks
    - Localhost-only deployments

    NEVER expose this endpoint to:
    - Public networks
    - Untrusted users
    - Production environments without strict authentication

    Security recommendations:
    - Add IP whitelisting
    - Implement command whitelisting
    - Run in containerized environment
    - Add comprehensive audit logging
    - Consider disabling entirely in production

    Note: This feature requires Unix PTY support and is not available on Windows.
    """
    import hmac

    # Authenticate: check for API key in query params
    api_key = websocket.query_params.get("api_key")
    from ignition_toolkit.core.config import get_settings
    expected_key = get_settings().websocket_api_key

    if not api_key or not hmac.compare_digest(api_key, expected_key):
        logger.warning(f"Unauthorized shell WebSocket connection attempt from {websocket.client}")
        await websocket.close(code=1008, reason="Unauthorized")
        return

    # Get working directory from query params
    working_dir = websocket.query_params.get("path", str(get_playbooks_dir().resolve()))

    await websocket.accept()
    logger.info(f"Shell WebSocket connected, working directory: {working_dir}")

    # PTY terminal sessions are not supported on Windows
    if IS_WINDOWS:
        await websocket.send_json(
            {"type": "error", "message": "Shell terminal is not supported on Windows"}
        )
        await websocket.close(code=1008, reason="Not supported on Windows")
        return

    master_fd = None
    process = None

    try:
        # Validate working directory exists
        if not os.path.isdir(working_dir):
            await websocket.send_json(
                {"type": "error", "message": f"Directory does not exist: {working_dir}"}
            )
            await websocket.close(code=1008, reason="Invalid directory")
            return

        # Spawn bash with PTY
        master_fd, slave_fd = pty.openpty()

        # Start bash in the specified directory
        process = subprocess.Popen(
            ["/bin/bash"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=working_dir,
            preexec_fn=os.setsid,  # Create new process group
            close_fds=True,
            env={**os.environ, "PS1": "$ "},  # Simple prompt
        )

        os.close(slave_fd)  # Parent doesn't need slave_fd

        logger.info(f"Bash shell started: PID={process.pid}, cwd={working_dir}")

        # Create tasks for bidirectional I/O
        async def read_from_pty():
            """Read output from PTY and send to WebSocket"""
            while True:
                try:
                    # Check if process is still alive
                    if process.poll() is not None:
                        logger.info(f"Shell process exited: {process.pid}")
                        await websocket.send_json({"type": "exit", "code": process.returncode})
                        break

                    # Use select to check if data is available (non-blocking)
                    readable, _, _ = select.select([master_fd], [], [], 0.1)
                    if readable:
                        data = os.read(master_fd, 1024)
                        if not data:
                            break
                        # Send as JSON with output field
                        try:
                            decoded = data.decode("utf-8", errors="replace")
                            await websocket.send_json({"output": decoded})
                        except Exception as e:
                            logger.error(f"Error decoding output: {e}")
                    else:
                        # Small sleep to prevent busy loop
                        await asyncio.sleep(0.01)

                except OSError:
                    break
                except Exception as e:
                    logger.error(f"Error reading from PTY: {e}")
                    break

        async def write_to_pty():
            """Receive data from WebSocket and write to PTY"""
            while True:
                try:
                    message = await websocket.receive_json()

                    if "input" in message:
                        # Text input from terminal
                        data = message["input"]
                        os.write(master_fd, data.encode("utf-8"))

                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error writing to PTY: {e}")
                    break

        # Run both tasks concurrently
        await asyncio.gather(read_from_pty(), write_to_pty(), return_exceptions=True)

    except Exception as e:
        logger.exception(f"Shell WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass  # WebSocket already closed

    finally:
        # Cleanup
        logger.info(f"Cleaning up shell session, PID: {process.pid if process else 'N/A'}")

        if process:
            try:
                # Try graceful termination first
                if process.poll() is None:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        # Force kill if still running
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        process.wait()
            except Exception as e:
                logger.error(f"Error terminating shell process: {e}")

        if master_fd is not None:
            try:
                os.close(master_fd)
            except Exception:
                pass

        try:
            await websocket.close()
        except Exception:
            pass



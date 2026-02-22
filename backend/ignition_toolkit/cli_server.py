"""
Cross-platform server management commands

Replaces bash-only scripts (start_server.sh, stop_server.sh, check_server.sh)
with Python commands that work on Windows, Linux, and macOS.

v4.1.0: Enhanced with pre-flight checks to prevent restart/refresh issues.
"""
import subprocess
import sys
import time
from pathlib import Path

import click
import psutil
from rich.console import Console

console = Console()


def find_server_processes():
    """Find all uvicorn processes for ignition_toolkit"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'uvicorn' in ' '.join(cmdline) and 'ignition_toolkit' in ' '.join(cmdline):
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return processes


def is_port_in_use(port=5000):
    """Check if port is in use"""
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            return True
    return False


# ==============================================================================
# Pre-flight Check Functions (v4.1.0)
# ==============================================================================

def get_package_root() -> Path:
    """Get the package root directory"""
    return Path(__file__).parent.parent


def check_frontend_staleness() -> tuple[str, str | None]:
    """
    Check if frontend build is older than source files

    Returns:
        tuple: (status, newest_file)
            status: 'missing', 'stale', or 'fresh'
            newest_file: name of newest source file if stale, None otherwise
    """
    package_root = get_package_root()
    dist_index = package_root / "frontend" / "dist" / "index.html"

    if not dist_index.exists():
        return ("missing", None)

    dist_mtime = dist_index.stat().st_mtime
    src_dir = package_root / "frontend" / "src"

    if not src_dir.exists():
        return ("fresh", None)  # No source to check against

    # Find all TypeScript/JavaScript source files
    src_files = list(src_dir.rglob("*.tsx")) + list(src_dir.rglob("*.ts")) + \
                list(src_dir.rglob("*.jsx")) + list(src_dir.rglob("*.js"))

    if not src_files:
        return ("fresh", None)

    # Check if any source file is newer than the build
    stale_files = [f for f in src_files if f.stat().st_mtime > dist_mtime]

    if stale_files:
        newest = max(stale_files, key=lambda f: f.stat().st_mtime)
        return ("stale", newest.name)

    return ("fresh", None)


def rebuild_frontend(quiet: bool = False) -> bool:
    """
    Rebuild the frontend

    Args:
        quiet: Suppress output if True

    Returns:
        bool: True if successful, False otherwise
    """
    package_root = get_package_root()
    rebuild_script = package_root / "rebuild-frontend.sh"

    if not rebuild_script.exists():
        # Fallback: try npm directly
        frontend_dir = package_root / "frontend"
        if not frontend_dir.exists():
            if not quiet:
                console.print("[red]✗ Frontend directory not found[/red]")
            return False

        try:
            if not quiet:
                console.print("[cyan]Building frontend...[/cyan]")

            subprocess.run(
                ["npm", "run", "build"],
                cwd=frontend_dir,
                capture_output=quiet,
                text=True,
                check=True
            )

            if not quiet:
                console.print("[green]✓ Frontend built successfully[/green]")
            return True

        except subprocess.CalledProcessError as e:
            if not quiet:
                console.print(f"[red]✗ Frontend build failed: {e}[/red]")
            return False
        except FileNotFoundError:
            if not quiet:
                console.print("[red]✗ npm not found. Please install Node.js[/red]")
            return False

    # Use the rebuild script
    try:
        if not quiet:
            console.print("[cyan]Running frontend rebuild...[/cyan]")

        subprocess.run(
            ["bash", str(rebuild_script)],
            capture_output=quiet,
            text=True,
            check=True
        )

        if not quiet:
            console.print("[green]✓ Frontend rebuilt successfully[/green]")
        return True

    except subprocess.CalledProcessError as e:
        if not quiet:
            console.print(f"[red]✗ Frontend rebuild failed: {e}[/red]")
        return False


def clear_bytecode_cache() -> int:
    """
    Clear Python bytecode cache files

    Returns:
        int: Number of cache directories removed
    """
    package_root = get_package_root()
    ignition_toolkit_dir = package_root / "ignition_toolkit"

    if not ignition_toolkit_dir.exists():
        return 0

    count = 0
    for pycache_dir in ignition_toolkit_dir.rglob("__pycache__"):
        try:
            import shutil
            shutil.rmtree(pycache_dir)
            count += 1
        except OSError:
            pass  # Ignore errors, cache clearing is best-effort

    return count


def check_database_locks() -> bool:
    """
    Check for SQLite database locks

    Returns:
        bool: True if no locks detected, False if locks found
    """
    from ignition_toolkit.core.paths import get_user_data_dir

    data_dir = get_user_data_dir()
    db_file = data_dir / "ignition_toolkit.db"

    if not db_file.exists():
        return True  # No database yet, no locks

    # If lock files (.db-wal, .db-shm) exist, that's actually normal for WAL mode
    # Only problematic if we can't open the database
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_file), timeout=1.0)
        conn.execute("SELECT 1")
        conn.close()
        return True
    except sqlite3.OperationalError:
        return False  # Database is locked
    except sqlite3.Error:
        return True  # Other SQLite errors, assume OK


def run_preflight_checks(skip_checks: bool = False, auto_rebuild: bool = True) -> bool:
    """
    Run all pre-flight checks before server start

    Args:
        skip_checks: Skip all checks if True
        auto_rebuild: Automatically rebuild frontend if stale

    Returns:
        bool: True if all checks passed, False otherwise
    """
    if skip_checks:
        console.print("[dim]Skipping pre-flight checks (--skip-checks)[/dim]")
        return True

    console.print("\n[bold cyan]Running pre-flight checks...[/bold cyan]\n")

    checks_passed = True

    # Check 1: Frontend staleness
    status, newest_file = check_frontend_staleness()

    if status == "missing":
        console.print("[red]✗ Frontend build missing[/red]")
        if auto_rebuild and click.confirm("  Build frontend now?", default=True):
            if rebuild_frontend():
                console.print("[green]✓ Frontend build created[/green]")
            else:
                console.print("[red]✗ Frontend build failed[/red]")
                checks_passed = False
        else:
            checks_passed = False

    elif status == "stale":
        console.print("[yellow]⚠ Frontend build is stale[/yellow]")
        console.print(f"  [dim]Source changed: {newest_file}[/dim]")
        if auto_rebuild:
            if click.confirm("  Rebuild frontend?", default=True):
                if rebuild_frontend():
                    console.print("[green]✓ Frontend rebuilt[/green]")
                else:
                    console.print("[yellow]⚠ Frontend rebuild failed, continuing with stale build[/yellow]")
        else:
            console.print("[dim]  (Auto-rebuild disabled)[/dim]")
    else:
        console.print("[green]✓ Frontend build is fresh[/green]")

    # Check 2: Clear bytecode cache
    cache_count = clear_bytecode_cache()
    if cache_count > 0:
        console.print(f"[green]✓ Cleared {cache_count} bytecode cache director{'y' if cache_count == 1 else 'ies'}[/green]")
    else:
        console.print("[green]✓ No bytecode cache to clear[/green]")

    # Check 3: Database locks
    if check_database_locks():
        console.print("[green]✓ Database accessible[/green]")
    else:
        console.print("[red]✗ Database is locked (may be in use by another process)[/red]")
        console.print("[yellow]  Try: ignition-toolkit server stop --force[/yellow]")
        checks_passed = False

    console.print()  # Empty line

    if checks_passed:
        console.print("[bold green]✓ All pre-flight checks passed[/bold green]\n")
    else:
        console.print("[bold red]✗ Some pre-flight checks failed[/bold red]\n")

    return checks_passed


@click.command()
@click.option('--port', default=5000, help='Port to run server on')
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--dev', is_flag=True, help='Development mode with auto-reload')
@click.option('--skip-checks', is_flag=True, help='Skip pre-flight checks (faster startup)')
@click.option('--no-rebuild', is_flag=True, help='Do not rebuild frontend even if stale')
def start(port, host, dev, skip_checks, no_rebuild):
    """
    Start the Ignition Toolkit server

    \b
    Examples:
      ignition-toolkit server start                    # Production mode
      ignition-toolkit server start --dev              # Development mode with auto-reload
      ignition-toolkit server start --skip-checks      # Skip pre-flight checks (faster)
      ignition-toolkit server start --port 8000        # Custom port
    """
    console.print("[bold cyan]Starting Ignition Automation Toolkit Server[/bold cyan]")

    # Check if server is already running
    processes = find_server_processes()
    if processes:
        console.print(f"[red]ERROR: Server already running ({len(processes)} process(es))[/red]")
        for proc in processes:
            console.print(f"  PID: {proc.pid}")
        console.print("\n[yellow]Run 'ignition-toolkit server stop' first[/yellow]")
        sys.exit(1)

    # Check if port is available
    if is_port_in_use(port):
        console.print(f"[red]ERROR: Port {port} is already in use[/red]")
        console.print("[yellow]Try a different port with --port option[/yellow]")
        sys.exit(1)

    # Set environment variables for consistent paths
    from ignition_toolkit.config import setup_environment
    setup_environment()

    # Run pre-flight checks (v4.1.0)
    auto_rebuild = not no_rebuild
    if not run_preflight_checks(skip_checks=skip_checks, auto_rebuild=auto_rebuild):
        console.print("[red]Server start aborted due to failed pre-flight checks[/red]")
        console.print("[yellow]Use --skip-checks to start anyway (not recommended)[/yellow]")
        sys.exit(1)

    # Display startup information
    console.print(f"[cyan]Starting server on http://{host}:{port}[/cyan]")
    if dev:
        console.print("[yellow]Development mode: auto-reload enabled[/yellow]")
        console.print("[dim]  Tip: Server will restart automatically when code changes[/dim]")
    else:
        console.print("[green]Production mode[/green]")
        console.print("[dim]  Tip: Use --dev flag for auto-reload during development[/dim]")

    console.print("\n[bold]Press CTRL+C to stop the server[/bold]\n")

    # Build uvicorn command
    uvicorn_cmd = [
        sys.executable, '-m', 'uvicorn',
        'ignition_toolkit.api.app:app',
        '--host', host,
        '--port', str(port)
    ]

    if dev:
        uvicorn_cmd.append('--reload')

    # Start server
    try:
        subprocess.run(uvicorn_cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error starting server: {e}[/red]")
        sys.exit(1)


@click.command()
@click.option('--force', is_flag=True, help='Force kill processes if normal termination fails')
def stop(force):
    """Stop the Ignition Toolkit server"""
    console.print("[bold cyan]Stopping Ignition Automation Toolkit Server[/bold cyan]")

    processes = find_server_processes()
    if not processes:
        console.print("[green]No server processes found (server not running)[/green]")
        return

    console.print(f"Found {len(processes)} server process(es)")

    # Try graceful termination first
    for proc in processes:
        try:
            console.print(f"Terminating process {proc.pid}...")
            proc.terminate()
        except psutil.NoSuchProcess:
            console.print(f"  Process {proc.pid} already gone")
        except psutil.AccessDenied:
            console.print(f"  [yellow]Access denied for process {proc.pid}[/yellow]")

    # Wait for processes to stop
    console.print("Waiting for processes to stop...")
    time.sleep(2)

    # Check if any still running
    remaining = find_server_processes()
    if remaining:
        if force:
            console.print(f"[yellow]{len(remaining)} process(es) didn't stop, forcing...[/yellow]")
            for proc in remaining:
                try:
                    console.print(f"Killing process {proc.pid}...")
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
                except psutil.AccessDenied:
                    console.print(f"  [red]Access denied for process {proc.pid}[/red]")

            time.sleep(1)
            final_check = find_server_processes()
            if final_check:
                console.print(f"[red]Warning: {len(final_check)} process(es) could not be stopped[/red]")
                for proc in final_check:
                    console.print(f"  PID: {proc.pid}")
            else:
                console.print("[green]✓ All processes stopped[/green]")
        else:
            console.print(f"[yellow]Warning: {len(remaining)} process(es) didn't stop gracefully[/yellow]")
            for proc in remaining:
                console.print(f"  PID: {proc.pid}")
            console.print("\n[cyan]Try running with --force to kill remaining processes[/cyan]")
    else:
        console.print("[green]✓ Server stopped successfully[/green]")


@click.command()
@click.option('--port', default=5000, help='Port to check')
def status(port):
    """Check server status and health"""
    console.print("[bold cyan]Ignition Toolkit Server Health Check[/bold cyan]\n")

    # Check for running processes
    processes = find_server_processes()
    if not processes:
        console.print("[red]✗ Server is NOT running[/red]")
        console.print("\n[yellow]To start server:[/yellow]")
        console.print("  ignition-toolkit server start")
        sys.exit(1)

    console.print("[green]✓ Server process found[/green]")
    for proc in processes:
        console.print(f"  PID: {proc.pid}")

    # Check if port is listening
    if not is_port_in_use(port):
        console.print(f"[yellow]⚠ Port {port} is not listening (server may be starting)[/yellow]")
    else:
        console.print(f"[green]✓ Port {port} is listening[/green]")

    # Try HTTP health check
    try:
        import httpx

        console.print(f"\nChecking HTTP endpoint at http://localhost:{port}/...")
        response = httpx.get(f'http://localhost:{port}/', timeout=5)

        if response.status_code == 200:
            console.print(f"[green]✓ Server is responding (HTTP {response.status_code})[/green]")
        else:
            console.print(f"[yellow]⚠ Server returned HTTP {response.status_code}[/yellow]")

        # Try health endpoint
        try:
            health_response = httpx.get(f'http://localhost:{port}/api/health', timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                console.print("[green]✓ Health check passed[/green]")
                console.print(f"  Version: {health_data.get('version', 'unknown')}")
                console.print(f"  Status: {health_data.get('status', 'unknown')}")
        except httpx.HTTPError:
            pass  # Health endpoint optional

        # Summary
        console.print("\n[bold green]✓ Server is HEALTHY[/bold green]")
        console.print("\n[bold]Access the web UI:[/bold]")
        console.print(f"  http://localhost:{port}")
        console.print("\n[bold]Server Info:[/bold]")
        console.print(f"  PID: {processes[0].pid}")
        console.print(f"  Port: {port}")

    except ImportError:
        console.print("\n[yellow]⚠ httpx not installed, skipping HTTP health check[/yellow]")
        console.print("[green]Process is running but HTTP check not available[/green]")
    except Exception as e:
        console.print("\n[red]✗ Server not responding to HTTP requests[/red]")
        console.print(f"  Error: {e}")
        console.print("\n[yellow]Server process is running but may not be ready yet[/yellow]")
        sys.exit(1)


@click.group()
def server():
    """Server management commands (start, stop, status)"""
    pass


# Register subcommands
server.add_command(start)
server.add_command(stop)
server.add_command(status)

"""
Command-line interface for Ignition Automation Toolkit
"""

from pathlib import Path

import click
import uvicorn
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main() -> None:
    """Ignition Automation Toolkit - SCADA automation made simple"""
    pass


@main.command()
@click.option("--host", default=None, help="API server host (default: from settings)")
@click.option("--port", default=None, type=int, help="API server port (default: from settings)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str | None, port: int | None, reload: bool) -> None:
    """Start the API server and web UI"""
    import logging

    # Configure logging FIRST - set to DEBUG to see all logs including perspective handler logs
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Import settings to get defaults from .env or Settings
    from ignition_toolkit.core.config import get_settings

    settings = get_settings()

    # Use CLI args if provided, otherwise use settings
    actual_host = host or settings.api_host
    actual_port = port or settings.api_port

    console.print(
        Panel.fit(
            "[bold cyan]Ignition Automation Toolkit[/bold cyan]\n"
            f"Server starting on http://{actual_host}:{actual_port}",
            border_style="cyan",
        )
    )

    uvicorn.run(
        "ignition_toolkit.api.app:app",
        host=actual_host,
        port=actual_port,
        reload=reload,
        log_level="info",
    )


@main.command()
def init() -> None:
    """Initialize credential vault and configuration"""
    from ignition_toolkit.credentials.vault import CredentialVault

    console.print("\n[bold cyan]Initializing Ignition Automation Toolkit...[/bold cyan]\n")

    # Create credential vault
    vault = CredentialVault()
    vault_path = vault.vault_path

    console.print(f"✅ Credential vault created: [green]{vault_path}[/green]")
    console.print(f"✅ Encryption key generated: [green]{vault_path / 'encryption.key'}[/green]")
    console.print(
        "\n[yellow]⚠️  Keep your encryption key safe! Loss of key = loss of credentials[/yellow]"
    )

    # Create data directory
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    console.print(f"✅ Data directory created: [green]{data_dir.absolute()}[/green]")

    # Create playbooks directory
    playbooks_dir = Path("./playbooks")
    playbooks_dir.mkdir(exist_ok=True)
    console.print(f"✅ Playbooks directory created: [green]{playbooks_dir.absolute()}[/green]")

    console.print("\n[bold green]✅ Initialization complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Run: [cyan]ignition-toolkit serve[/cyan]")
    console.print("  2. Open: [cyan]http://localhost:5000[/cyan]")
    console.print("  3. Add credentials via web UI or CLI\n")


@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def verify(verbose: bool) -> None:
    """Verify installation and configuration"""
    import os
    import subprocess
    import sys
    from pathlib import Path

    from rich.table import Table

    from ignition_toolkit.core.paths import (
        get_package_root,
        get_playbooks_dir,
        get_user_data_dir,
    )

    console.print("\n[bold cyan]Verifying Ignition Automation Toolkit Installation[/bold cyan]\n")

    checks = []
    errors = []
    warnings = []

    # 1. Python version check
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    python_ok = sys.version_info >= (3, 10)
    checks.append(("Python Version", f"{python_version}", "✅" if python_ok else "❌"))
    if not python_ok:
        errors.append(f"Python 3.10+ required, found {python_version}")

    # 2. Package root check
    try:
        package_root = get_package_root()
        package_root_ok = package_root.exists()
        checks.append(("Package Root", str(package_root), "✅" if package_root_ok else "❌"))
        if not package_root_ok:
            errors.append(f"Package root not found: {package_root}")
    except Exception as e:
        checks.append(("Package Root", "ERROR", "❌"))
        errors.append(f"Package root check failed: {e}")

    # 3. Playbooks directory check
    try:
        playbooks_dir = get_playbooks_dir()
        playbooks_ok = playbooks_dir.exists()
        checks.append(("Playbooks Directory", str(playbooks_dir), "✅" if playbooks_ok else "⚠️"))
        if not playbooks_ok:
            warnings.append(f"Playbooks directory not found: {playbooks_dir} (run 'init')")
    except Exception as e:
        checks.append(("Playbooks Directory", "ERROR", "❌"))
        errors.append(f"Playbooks directory check failed: {e}")

    # 4. User data directory check
    try:
        user_data_dir = get_user_data_dir()
        user_data_ok = user_data_dir.exists()
        checks.append(("User Data Directory", str(user_data_dir), "✅" if user_data_ok else "⚠️"))
        if not user_data_ok:
            warnings.append(f"User data directory not found: {user_data_dir} (run 'init')")
    except Exception as e:
        checks.append(("User Data Directory", "ERROR", "❌"))
        errors.append(f"User data directory check failed: {e}")

    # 5. Credential vault check
    try:
        from ignition_toolkit.credentials.vault import CredentialVault

        vault = CredentialVault()
        vault_ok = vault.vault_path.exists()
        key_exists = (vault.vault_path / "encryption.key").exists()
        checks.append(("Credential Vault", str(vault.vault_path), "✅" if vault_ok else "⚠️"))
        if not vault_ok:
            warnings.append(f"Credential vault not initialized (run 'init')")
        elif not key_exists:
            warnings.append("Encryption key not found")
    except Exception as e:
        checks.append(("Credential Vault", "ERROR", "❌"))
        errors.append(f"Credential vault check failed: {e}")

    # 6. Database check
    try:
        from ignition_toolkit.core.config import get_settings

        settings = get_settings()
        db_path = settings.database_path
        db_ok = db_path.exists()
        checks.append(("Database", str(db_path), "✅" if db_ok else "⚠️"))
        if not db_ok:
            warnings.append(f"Database not found: {db_path} (will be created on first use)")
    except Exception as e:
        checks.append(("Database", "ERROR", "❌"))
        errors.append(f"Database check failed: {e}")

    # 7. Frontend build check
    try:
        frontend_dist = package_root / "frontend" / "dist"
        frontend_ok = frontend_dist.exists() and (frontend_dist / "index.html").exists()
        checks.append(("Frontend Build", str(frontend_dist), "✅" if frontend_ok else "⚠️"))
        if not frontend_ok:
            warnings.append(
                "Frontend not built (run 'cd frontend && npm install && npm run build')"
            )
    except Exception as e:
        checks.append(("Frontend Build", "ERROR", "❌"))
        errors.append(f"Frontend check failed: {e}")

    # 8. Playwright browsers check
    try:
        playwright_path = os.getenv("PLAYWRIGHT_BROWSERS_PATH", str(package_root / "data" / ".playwright-browsers"))
        playwright_ok = Path(playwright_path).exists()
        checks.append(("Playwright Browsers", playwright_path, "✅" if playwright_ok else "⚠️"))
        if not playwright_ok:
            warnings.append(f"Playwright browsers not installed (run 'playwright install chromium')")
    except Exception as e:
        checks.append(("Playwright Browsers", "ERROR", "❌"))
        errors.append(f"Playwright check failed: {e}")

    # 9. Dependencies check (sample key packages)
    key_packages = ["fastapi", "uvicorn", "httpx", "playwright", "yaml", "cryptography"]
    for pkg in key_packages:
        try:
            __import__(pkg)
            if verbose:
                checks.append((f"Package: {pkg}", "installed", "✅"))
        except ImportError:
            checks.append((f"Package: {pkg}", "NOT INSTALLED", "❌"))
            errors.append(f"Required package '{pkg}' not installed")

    # 10. .env file check (optional)
    env_file = package_root / ".env"
    env_ok = env_file.exists()
    if verbose or not env_ok:
        checks.append((".env Configuration", str(env_file), "✅" if env_ok else "⚠️"))
        if not env_ok:
            warnings.append(".env file not found (copy from .env.example)")

    # Display results
    table = Table(title="Installation Verification", show_header=True, header_style="bold cyan")
    table.add_column("Check", style="white")
    table.add_column("Location/Value", style="dim")
    table.add_column("Status", style="white")

    for check_name, check_value, check_status in checks:
        # Truncate long paths
        if len(check_value) > 60 and not verbose:
            check_value = "..." + check_value[-57:]
        table.add_row(check_name, check_value, check_status)

    console.print(table)
    console.print()

    # Show warnings
    if warnings:
        console.print("[bold yellow]⚠️  Warnings:[/bold yellow]")
        for warning in warnings:
            console.print(f"  • {warning}")
        console.print()

    # Show errors
    if errors:
        console.print("[bold red]❌ Errors:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        console.print()
        console.print("[red]Installation has critical issues. Please fix the errors above.[/red]\n")
        sys.exit(1)

    # Success
    if not warnings:
        console.print("[bold green]✅ All checks passed! Installation is healthy.[/bold green]\n")
    else:
        console.print("[bold yellow]✅ Installation is functional but has warnings.[/bold yellow]")
        console.print("[dim]Fix warnings for optimal operation.[/dim]\n")

    # Next steps
    console.print("[bold]Next steps:[/bold]")
    console.print("  • Run: [cyan]ignition-toolkit serve[/cyan]")
    console.print("  • Access: [cyan]http://localhost:5000[/cyan]")
    console.print("  • For detailed output: [cyan]ignition-toolkit verify --verbose[/cyan]\n")


@main.group()
def credential() -> None:
    """Manage credentials"""
    pass


@credential.command("add")
@click.argument("name")
@click.option("--username", prompt=True, help="Username")
@click.option("--password", prompt=True, hide_input=True, help="Password")
@click.option("--gateway-url", default=None, help="Gateway URL (e.g., http://localhost:9088)")
@click.option("--description", default="", help="Credential description")
def credential_add(name: str, username: str, password: str, gateway_url: str | None, description: str) -> None:
    """Add a new credential"""
    from ignition_toolkit.credentials.models import Credential
    from ignition_toolkit.credentials.vault import CredentialVault

    vault = CredentialVault()
    credential = Credential(
        name=name,
        username=username,
        password=password,
        gateway_url=gateway_url,
        description=description,
    )
    vault.save_credential(credential)

    console.print(f"\n✅ Credential '[cyan]{name}[/cyan]' saved successfully")
    if gateway_url:
        console.print(f"   Gateway URL: [green]{gateway_url}[/green]")
    console.print(f"   Use in playbooks: [yellow]{{{{ credential.{name} }}}}[/yellow]\n")


@credential.command("list")
def credential_list() -> None:
    """List all stored credentials"""
    from rich.table import Table

    from ignition_toolkit.credentials.vault import CredentialVault

    vault = CredentialVault()
    credentials = vault.list_credentials()

    if not credentials:
        console.print("\n[yellow]No credentials stored yet[/yellow]")
        console.print("Add one with: [cyan]ignition-toolkit credential add <name>[/cyan]\n")
        return

    table = Table(title="Stored Credentials", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan")
    table.add_column("Username", style="white")
    table.add_column("Gateway URL", style="green")
    table.add_column("Description", style="dim")

    for cred in credentials:
        table.add_row(cred.name, cred.username, cred.gateway_url or "", cred.description or "")

    console.print()
    console.print(table)
    console.print()


@credential.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to delete this credential?")
def credential_delete(name: str) -> None:
    """Delete a credential"""
    from ignition_toolkit.credentials.vault import CredentialVault

    vault = CredentialVault()
    vault.delete_credential(name)

    console.print(f"\n✅ Credential '[cyan]{name}[/cyan]' deleted\n")


@main.group()
def playbook() -> None:
    """Manage playbooks"""
    pass


@playbook.command("list")
def playbook_list() -> None:
    """List available playbooks"""
    from pathlib import Path

    from rich.table import Table

    playbooks_dir = Path("./playbooks")
    if not playbooks_dir.exists():
        console.print("\n[yellow]No playbooks directory found[/yellow]\n")
        return

    yaml_files = list(playbooks_dir.rglob("*.yaml")) + list(playbooks_dir.rglob("*.yml"))

    if not yaml_files:
        console.print("\n[yellow]No playbooks found[/yellow]")
        console.print("Create one in: [cyan]./playbooks/[/cyan]\n")
        return

    table = Table(title="Available Playbooks", show_header=True, header_style="bold cyan")
    table.add_column("Path", style="cyan")
    table.add_column("Size", style="white")

    for yaml_file in sorted(yaml_files):
        rel_path = yaml_file.relative_to(playbooks_dir)
        size = f"{yaml_file.stat().st_size / 1024:.1f} KB"
        table.add_row(str(rel_path), size)

    console.print()
    console.print(table)
    console.print()


@playbook.command("run")
@click.argument("playbook_path", type=click.Path(exists=True))
@click.option("--param", "-p", multiple=True, help="Parameter in format name=value")
@click.option("--gateway-url", help="Gateway URL (alternative to --param)")
@click.option("--gateway-username", help="Gateway username")
@click.option("--gateway-credential", help="Gateway credential name from vault")
def playbook_run(
    playbook_path: str,
    param: tuple,
    gateway_url: str | None,
    gateway_username: str | None,
    gateway_credential: str | None,
) -> None:
    """Run a playbook"""
    import asyncio
    from pathlib import Path

    from rich.progress import Progress, SpinnerColumn, TextColumn

    from ignition_toolkit.credentials import CredentialVault
    from ignition_toolkit.gateway import GatewayClient
    from ignition_toolkit.playbook.engine import PlaybookEngine
    from ignition_toolkit.playbook.loader import PlaybookLoader
    from ignition_toolkit.storage import get_database

    # Load playbook
    console.print(f"\n[bold cyan]Loading playbook:[/bold cyan] {playbook_path}\n")
    loader = PlaybookLoader()
    playbook = loader.load_from_file(Path(playbook_path))

    console.print(f"  Name: [green]{playbook.name}[/green]")
    console.print(f"  Version: [green]{playbook.version}[/green]")
    console.print(f"  Steps: [green]{len(playbook.steps)}[/green]\n")

    # Parse parameters
    parameters = {}
    for p in param:
        if "=" not in p:
            console.print(f"[red]Invalid parameter format: {p}[/red]")
            console.print("Use: --param name=value\n")
            return
        name, value = p.split("=", 1)
        parameters[name] = value

    # Add gateway parameters if provided
    if gateway_url:
        parameters["gateway_url"] = gateway_url
    if gateway_username:
        parameters["gateway_username"] = gateway_username
    if gateway_credential:
        parameters["gateway_credential"] = gateway_credential

    # Prompt for missing required parameters
    for param_def in playbook.parameters:
        if param_def.required and param_def.name not in parameters:
            if param_def.type.value == "credential":
                console.print(f"[yellow]Required credential parameter:[/yellow] {param_def.name}")
                console.print(f"Use: --param {param_def.name}=<credential_name>\n")
                return
            else:
                value = click.prompt(f"Enter value for '{param_def.name}' ({param_def.type.value})")
                parameters[param_def.name] = value

    # Initialize components
    vault = CredentialVault()
    database = get_database()
    gateway_client = None

    # Create Gateway client if needed
    if gateway_url:
        gateway_client = GatewayClient(gateway_url)

    # Execute playbook
    async def run():
        engine = PlaybookEngine(
            gateway_client=gateway_client,
            credential_vault=vault,
            database=database,
        )

        console.print("[bold cyan]Executing playbook...[/bold cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running...", total=None)

            def update_callback(state):
                step_count = len(state.step_results)
                total_steps = len(playbook.steps)
                progress.update(task, description=f"Step {step_count}/{total_steps}")

            engine.set_update_callback(update_callback)

            try:
                if gateway_client:
                    await gateway_client.__aenter__()

                execution_state = await engine.execute_playbook(
                    playbook, parameters, base_path=Path(playbook_path).parent
                )

                progress.stop()

                # Show results
                console.print("\n[bold]Execution Status:[/bold] ", end="")
                if execution_state.status.value == "completed":
                    console.print(f"[bold green]{execution_state.status.value}[/bold green]")
                elif execution_state.status.value == "failed":
                    console.print(f"[bold red]{execution_state.status.value}[/bold red]")
                    if execution_state.error:
                        console.print(f"[red]Error: {execution_state.error}[/red]")
                else:
                    console.print(f"[bold yellow]{execution_state.status.value}[/bold yellow]")

                # Show step results
                from rich.table import Table

                table = Table(title="Step Results", show_header=True, header_style="bold cyan")
                table.add_column("Step ID", style="cyan")
                table.add_column("Status", style="white")
                table.add_column("Duration", style="dim")

                for result in execution_state.step_results:
                    if result.completed_at and result.started_at:
                        duration = (result.completed_at - result.started_at).total_seconds()
                        duration_str = f"{duration:.1f}s"
                    else:
                        duration_str = "-"

                    status_color = {
                        "completed": "green",
                        "failed": "red",
                        "skipped": "yellow",
                    }.get(result.status.value, "white")

                    table.add_row(
                        result.step_id,
                        f"[{status_color}]{result.status.value}[/{status_color}]",
                        duration_str,
                    )

                console.print()
                console.print(table)
                console.print()

            finally:
                if gateway_client:
                    await gateway_client.__aexit__(None, None, None)

    asyncio.run(run())


@playbook.command("export")
@click.argument("playbook_path", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output JSON file path")
def playbook_export(playbook_path: str, output: str | None) -> None:
    """Export playbook to JSON for sharing"""
    from pathlib import Path

    from ignition_toolkit.playbook.exporter import PlaybookExporter
    from ignition_toolkit.playbook.loader import PlaybookLoader

    # Load playbook
    loader = PlaybookLoader()
    playbook = loader.load_from_file(Path(playbook_path))

    # Export to JSON
    exporter = PlaybookExporter()
    json_data = exporter.export(playbook)

    # Determine output path
    if output is None:
        output = str(Path(playbook_path).with_suffix(".json"))

    Path(output).write_text(json_data)

    console.print(f"\n✅ Playbook exported to: [green]{output}[/green]")
    console.print("   Share this file with colleagues\n")


@playbook.command("import")
@click.argument("json_path", type=click.Path(exists=True))
@click.option("--output-dir", default="./playbooks/imported", help="Output directory")
def playbook_import(json_path: str, output_dir: str) -> None:
    """Import playbook from JSON"""
    from pathlib import Path

    from ignition_toolkit.playbook.exporter import PlaybookExporter

    # Import from JSON
    exporter = PlaybookExporter()
    playbook = exporter.import_from_json(Path(json_path).read_text())

    # Save to YAML
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    yaml_path = output_path / f"{playbook.name.lower().replace(' ', '_')}.yaml"

    from ignition_toolkit.playbook.loader import PlaybookLoader

    loader = PlaybookLoader()
    loader.save_to_file(playbook, yaml_path)

    console.print(f"\n✅ Playbook imported to: [green]{yaml_path}[/green]")
    console.print(f"   Run with: [cyan]ignition-toolkit playbook run {yaml_path}[/cyan]\n")


# Import and register server management commands
from ignition_toolkit.cli_server import server

main.add_command(server)


if __name__ == "__main__":
    main()

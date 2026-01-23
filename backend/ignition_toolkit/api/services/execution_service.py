"""
Execution Service

High-level execution orchestration service.
Extracts business logic from executions.py router (reducing from 1,220 lines).
"""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from fastapi import HTTPException

from ignition_toolkit.api.services.credential_manager import CredentialManager
from ignition_toolkit.core.validation import PathValidator
from ignition_toolkit.credentials import CredentialVault
from ignition_toolkit.gateway import GatewayClient
from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.playbook.execution_manager import ExecutionManager
from ignition_toolkit.playbook.loader import PlaybookLoader
from ignition_toolkit.playbook.models import ExecutionState, ExecutionStatus, Playbook
from ignition_toolkit.storage import Database

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    High-level execution orchestration service

    Responsibilities:
    - Load and validate playbooks
    - Apply credential autofill
    - Create and configure PlaybookEngine
    - Start background execution tasks
    - Manage execution lifecycle

    This service consolidates logic previously scattered across:
    - validate_and_resolve_playbook_path
    - apply_credential_autofill
    - create_playbook_engine_with_callbacks
    - create_execution_runner
    - create_timeout_watchdog
    - broadcast_initial_execution_state
    """

    def __init__(
        self,
        execution_manager: ExecutionManager,
        credential_vault: CredentialVault,
        database: Database,
        screenshot_callback: Callable[[str, str], None] | None = None,
        state_update_callback: Callable[[ExecutionState], None] | None = None,
    ):
        """
        Initialize execution service

        Args:
            execution_manager: ExecutionManager for lifecycle management
            credential_vault: CredentialVault for credential access
            database: Database for persistence
            screenshot_callback: Callback for screenshot broadcasts
            state_update_callback: Callback for execution state updates
        """
        self.execution_manager = execution_manager
        self.credential_manager = CredentialManager(vault=credential_vault)
        self.credential_vault = credential_vault
        self.database = database
        self.screenshot_callback = screenshot_callback
        self.state_update_callback = state_update_callback

    async def start_execution(
        self,
        playbook_path: str,
        parameters: dict,
        gateway_url: str | None = None,
        credential_name: str | None = None,
        debug_mode: bool = False,
        timeout_seconds: int = 3600,
        timeout_overrides: dict[str, int] | None = None,
    ) -> str:
        """
        Start playbook execution with credential autofill

        Args:
            playbook_path: Relative path to playbook file
            parameters: Execution parameters
            gateway_url: Optional Gateway URL
            credential_name: Optional credential name for autofill
            debug_mode: Enable debug mode (pause on failures)
            timeout_seconds: Execution timeout (default: 1 hour)
            timeout_overrides: Optional per-playbook timeout overrides
                - gateway_restart: Gateway restart timeout in seconds
                - module_install: Module installation timeout in seconds
                - browser_operation: Browser operation timeout in milliseconds

        Returns:
            Execution ID (UUID string)

        Raises:
            HTTPException: If playbook not found or validation fails
        """
        # Step 1: Validate and load playbook
        playbooks_dir, full_playbook_path = PathValidator.validate_and_resolve(
            playbook_path, must_exist=True
        )
        playbook = PlaybookLoader.load_from_file(full_playbook_path)

        # Step 1.5: Ensure browser is installed for playbooks that need it
        playbook_domain = playbook.metadata.get("domain")
        if playbook_domain and playbook_domain.lower() != "gateway":
            await self._ensure_browser_available()

        # Step 2: Apply credential autofill
        gateway_url, parameters = self.credential_manager.apply_autofill(
            playbook=playbook,
            credential_name=credential_name,
            gateway_url=gateway_url,
            parameters=parameters,
        )

        # Step 3: Generate execution ID
        execution_id = str(uuid.uuid4())

        # Step 4: Create PlaybookEngine with callbacks
        engine, gateway_client = await self._create_engine(
            gateway_url=gateway_url,
            execution_id=execution_id,
            debug_mode=debug_mode,
            timeout_overrides=timeout_overrides,
        )

        # Step 5: Initial state broadcast - SKIP (engine handles this to avoid duplicates)
        # The engine will broadcast initial state when execute_playbook() is called

        # Step 6: Create and start background execution
        runner = self._create_runner(
            engine=engine,
            playbook=playbook,
            parameters=parameters,
            playbook_path=full_playbook_path,
            execution_id=execution_id,
            gateway_client=gateway_client,
        )

        await self.execution_manager.start_execution(
            execution_id=execution_id,
            engine=engine,
            runner=runner,
        )

        # Step 7: Start timeout watchdog
        task = self.execution_manager.get_task(execution_id)
        if task:
            asyncio.create_task(
                self._timeout_watchdog(execution_id, task, engine, timeout_seconds)
            )

        logger.info(
            f"Started execution {execution_id} for playbook '{playbook.name}' "
            f"(debug_mode={debug_mode}, timeout={timeout_seconds}s)"
        )

        return execution_id

    async def _create_engine(
        self,
        gateway_url: str | None,
        execution_id: str,
        debug_mode: bool,
        timeout_overrides: dict[str, int] | None = None,
    ) -> tuple[PlaybookEngine, GatewayClient | None]:
        """
        Create PlaybookEngine with all necessary dependencies and callbacks

        Args:
            gateway_url: Optional Gateway URL
            execution_id: Execution UUID
            debug_mode: Enable debug mode
            timeout_overrides: Optional per-playbook timeout overrides

        Returns:
            Tuple of (engine, gateway_client)
        """
        gateway_client = None
        if gateway_url:
            gateway_client = GatewayClient(gateway_url)

        # Create screenshot callback wrapper
        async def screenshot_cb(exec_id: str, screenshot_b64: str):
            if self.screenshot_callback:
                await self.screenshot_callback(exec_id, screenshot_b64)

        # Create engine
        engine = PlaybookEngine(
            gateway_client=gateway_client,
            credential_vault=self.credential_vault,
            database=self.database,
            screenshot_callback=screenshot_cb,
            timeout_overrides=timeout_overrides,
        )

        # Set debug mode
        if debug_mode:
            engine.state_manager.enable_debug_mode()

        # Set up state update callback
        if self.state_update_callback:

            async def broadcast_update(state: ExecutionState):
                await self.state_update_callback(state)

            engine.set_update_callback(broadcast_update)

        return engine, gateway_client

    async def _broadcast_initial_state(self, execution_id: str, playbook: Playbook) -> None:
        """
        Broadcast initial execution state with all steps as "pending"

        Args:
            execution_id: Execution UUID
            playbook: Loaded playbook object
        """
        if not self.state_update_callback:
            return

        # Create initial step results with all steps as "pending"
        from ignition_toolkit.playbook.models import StepResult, StepStatus

        initial_step_results = [
            StepResult(
                step_id=step.id,
                step_name=step.name,
                status=StepStatus.PENDING,
                started_at=None,
                completed_at=None,
                error=None,
                output={},
            )
            for step in playbook.steps
        ]

        initial_state = ExecutionState(
            execution_id=execution_id,
            playbook_name=playbook.name,
            status=ExecutionStatus.RUNNING,
            current_step_index=None,
            started_at=datetime.now(),
            step_results=initial_step_results,
            domain=playbook.metadata.get("domain"),  # Include playbook domain
        )
        await self.state_update_callback(initial_state)
        logger.info(f"Broadcasted initial state with {len(initial_step_results)} steps for execution {execution_id}")

    def _create_runner(
        self,
        engine: PlaybookEngine,
        playbook: Playbook,
        parameters: dict,
        playbook_path: Path,
        execution_id: str,
        gateway_client: GatewayClient | None,
    ) -> Callable:
        """
        Create async function that runs the playbook execution

        Args:
            engine: PlaybookEngine instance
            playbook: Loaded playbook object
            parameters: Execution parameters
            playbook_path: Path to playbook file
            execution_id: Execution UUID
            gateway_client: Optional Gateway client

        Returns:
            Async function that executes the playbook
        """

        async def run_execution():
            """Execute playbook in background"""
            logger.info(f"Starting background execution for {execution_id}")

            try:
                # Enter gateway client context if present
                if gateway_client:
                    await gateway_client.__aenter__()

                # Execute playbook
                execution_state = await engine.execute_playbook(
                    playbook,
                    parameters,
                    base_path=playbook_path.parent,
                    execution_id=execution_id,
                    playbook_path=playbook_path,
                )

                logger.info(
                    f"Execution {execution_state.execution_id} completed with "
                    f"status: {execution_state.status}"
                )

                # Mark completion
                self.execution_manager.mark_completed(execution_id)

            except asyncio.CancelledError:
                logger.warning(f"Execution {execution_id} was cancelled")
                self.execution_manager.mark_completed(execution_id)
                await self._update_cancelled_status(execution_id, engine)
                raise

            except Exception as e:
                logger.exception(f"Error in execution {execution_id}: {e}")
                self.execution_manager.mark_completed(execution_id)

            finally:
                # Exit gateway client context
                if gateway_client:
                    await gateway_client.__aexit__(None, None, None)

                # NOTE: Task cleanup is handled by TTL mechanism, not here
                # Removing task too early prevents cancel endpoint from finding it
                # (Fixed in v3.44.13, ported to v4.0.2)

        return run_execution

    async def _update_cancelled_status(
        self, execution_id: str, engine: PlaybookEngine
    ) -> None:
        """
        Update database and broadcast cancellation status

        Args:
            execution_id: Execution UUID
            engine: PlaybookEngine instance
        """
        # Update database
        with self.database.session_scope() as session:
            from ignition_toolkit.storage import ExecutionModel

            execution = (
                session.query(ExecutionModel)
                .filter_by(execution_id=execution_id)
                .first()
            )
            if execution:
                execution.status = "cancelled"
                execution.completed_at = datetime.now()
                session.commit()
                logger.info(f"Updated execution {execution_id} status to 'cancelled'")

        # Broadcast cancellation
        if self.state_update_callback:
            execution_state = engine.get_current_execution()
            if execution_state:
                execution_state.status = ExecutionStatus.CANCELLED
                execution_state.completed_at = datetime.now()
                await self.state_update_callback(execution_state)
                logger.info(f"Broadcasted cancellation for {execution_id}")

    async def _timeout_watchdog(
        self,
        execution_id: str,
        task: asyncio.Task,
        engine: PlaybookEngine,
        timeout_seconds: int,
    ) -> None:
        """
        Auto-cancel execution if it runs too long

        Args:
            execution_id: Execution UUID
            task: Asyncio task to monitor
            engine: PlaybookEngine to cancel
            timeout_seconds: Timeout in seconds
        """
        try:
            await asyncio.sleep(timeout_seconds)
            if not task.done():
                logger.warning(f"Execution {execution_id} exceeded timeout - auto-cancelling")
                await engine.cancel()
                task.cancel()
        except asyncio.CancelledError:
            pass  # Watchdog cancelled (normal if execution finishes)
        except Exception as e:
            logger.exception(f"Error in timeout watchdog for {execution_id}: {e}")

    async def _ensure_browser_available(self) -> None:
        """
        Ensure Playwright browser is installed before running browser-based playbooks.

        This is called on-demand when executing Perspective or Designer playbooks,
        rather than blocking app startup with a large download.

        Raises:
            HTTPException: If browser installation fails
        """
        from ignition_toolkit.startup.playwright_installer import (
            ensure_browser_installed,
            is_browser_installed,
        )

        if is_browser_installed():
            return

        logger.info("Browser not installed - downloading Chromium (~170MB)...")

        try:
            success = await ensure_browser_installed()
            if not success:
                raise HTTPException(
                    status_code=503,
                    detail="Browser installation failed. Please check network connectivity and try again.",
                )
            logger.info("Browser installed successfully")
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Browser installation error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Browser installation failed: {e}",
            )

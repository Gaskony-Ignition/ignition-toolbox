"""
Playbook step handlers

Handles nested playbook execution using Strategy Pattern.
"""

import logging
from typing import Any

from ignition_toolkit.playbook.exceptions import StepExecutionError
from ignition_toolkit.playbook.executors.base import StepHandler

logger = logging.getLogger(__name__)


class PlaybookRunHandler(StepHandler):
    """
    Handle playbook.run step (nested playbook execution)

    This handler requires special initialization with the parent executor context
    to enable nested execution while sharing browser/gateway instances.
    """

    def __init__(self, parent_executor: Any):
        """
        Initialize playbook run handler

        Args:
            parent_executor: Reference to parent StepExecutor for nested execution
        """
        self.parent_executor = parent_executor

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute nested playbook as a single step (composable playbooks)

        Args:
            params: Resolved parameters including 'playbook' path

        Returns:
            Aggregated step output from nested playbook execution

        Raises:
            StepExecutionError: If playbook execution fails or validation fails
        """
        playbook_path = params.get("playbook")

        if not playbook_path:
            raise StepExecutionError("playbook", "Missing required parameter: playbook")

        # Convert to absolute path, searching user dir first then built-in
        from ignition_toolkit.core.paths import get_all_playbook_dirs
        from ignition_toolkit.playbook.loader import PlaybookLoader
        from ignition_toolkit.playbook.metadata import PlaybookMetadataStore

        metadata_store = PlaybookMetadataStore()

        # Resolve playbook path relative to playbooks root directory
        # Search user dir first so user-modified playbooks take priority
        full_path = None
        for playbooks_root in get_all_playbook_dirs():
            candidate = playbooks_root / playbook_path
            if candidate.exists():
                full_path = candidate
                break

        if full_path is None:
            raise StepExecutionError("playbook", f"Playbook not found: {playbook_path}")

        # Get relative path for metadata lookup (relative to playbooks root)
        relative_path = playbook_path

        # Verify that playbook is marked as verified
        metadata = metadata_store.get_metadata(relative_path)
        if not metadata.verified:
            raise StepExecutionError(
                "playbook",
                f"Playbook '{relative_path}' must be verified before it can be used as a step. "
                f"Mark it as verified via the UI 3-dot menu.",
            )

        # Check for circular dependencies (basic check)
        if hasattr(self.parent_executor, "_execution_stack"):
            if playbook_path in self.parent_executor._execution_stack:
                raise StepExecutionError(
                    "playbook",
                    f"Circular dependency detected: playbook '{playbook_path}' calls itself",
                )
        else:
            self.parent_executor._execution_stack = []

        # Add to execution stack
        self.parent_executor._execution_stack.append(playbook_path)

        # Check nesting depth
        MAX_NESTING_DEPTH = 3
        if len(self.parent_executor._execution_stack) > MAX_NESTING_DEPTH:
            self.parent_executor._execution_stack.pop()
            raise StepExecutionError(
                "playbook",
                f"Maximum nesting depth ({MAX_NESTING_DEPTH}) exceeded. "
                f"Current stack: {' -> '.join(self.parent_executor._execution_stack)}",
            )

        try:
            # Load nested playbook using static method
            nested_playbook = PlaybookLoader.load_from_file(full_path)

            # Extract parameters for child playbook (remove 'playbook' key)
            child_params = {k: v for k, v in params.items() if k != "playbook"}

            # Apply default values for missing optional parameters (Bug fix: nested playbooks need defaults)
            # This mirrors the logic in engine.py lines 239-245
            for param in nested_playbook.parameters:
                if param.name not in child_params and param.default is not None:
                    child_params[param.name] = param.default
                    logger.info(f"Applied default value for nested parameter '{param.name}': {param.default}")

            # Execute nested playbook using EXISTING browser and gateway from parent
            # This allows browser context to persist across nested calls
            logger.info(f"Executing nested playbook: {playbook_path}")
            logger.info(f"Child parameters: {child_params}")

            # Create a child StepExecutor that shares browser and gateway from parent
            from ignition_toolkit.playbook.parameters import ParameterResolver

            # Create step_results dictionary for nested playbook
            nested_step_results: dict[str, dict[str, Any]] = {}

            child_resolver = ParameterResolver(
                parameters=child_params,
                variables={},
                credential_vault=self.parent_executor.parameter_resolver.credential_vault
                if self.parent_executor.parameter_resolver
                else None,
                step_results=nested_step_results,
            )

            # Import StepExecutor here to avoid circular import at module level
            from ignition_toolkit.playbook.step_executor import StepExecutor

            child_executor = StepExecutor(
                gateway_client=self.parent_executor.gateway_client,  # Share parent's gateway client
                browser_manager=self.parent_executor.browser_manager,  # Share parent's browser manager
                designer_manager=self.parent_executor.designer_manager,  # Share parent's designer manager
                parameter_resolver=child_resolver,
                base_path=self.parent_executor.base_path,
                state_manager=self.parent_executor.state_manager,
                parent_engine=self.parent_executor.parent_engine,  # Pass parent engine for progress updates
            )
            child_executor._execution_stack = self.parent_executor._execution_stack.copy()

            # Execute all steps in the nested playbook
            nested_results = []
            nested_screenshots = []  # Track screenshots from nested execution

            for idx, step in enumerate(nested_playbook.steps, 1):
                logger.info(f"Executing nested step: {step.name}")

                # Update parent about nested step progress
                if self.parent_executor.parent_engine:
                    progress_info = {
                        "nested_playbook": playbook_path,
                        "nested_step": f"{idx}/{len(nested_playbook.steps)}",
                        "nested_step_name": step.name,
                        "nested_step_id": step.id,
                    }
                    # Find the playbook.run step in parent's execution state and update its output
                    try:
                        await self.parent_executor.parent_engine._update_nested_step_progress(progress_info)
                    except Exception as e:
                        logger.warning(f"Failed to update parent with nested step progress: {e}")

                step_result = await child_executor.execute_step(step)

                # Store step output for nested playbook step references
                if step_result.output:
                    nested_step_results[step.id] = step_result.output

                # Extract screenshot paths from step result output
                if step_result.output and isinstance(step_result.output, dict):
                    # Check for direct screenshot (browser.screenshot steps)
                    screenshot = step_result.output.get("screenshot")
                    if screenshot and isinstance(screenshot, str):
                        nested_screenshots.append(screenshot)

                    # Check for nested playbook screenshots (recursive)
                    nested_playbook_screenshots = step_result.output.get("screenshots", [])
                    if isinstance(nested_playbook_screenshots, list):
                        nested_screenshots.extend(nested_playbook_screenshots)

                # Store only JSON-serializable summary (not the full StepResult object)
                nested_results.append({
                    "step_id": step.id,
                    "step_name": step.name,
                    "status": step_result.status.value
                    if hasattr(step_result.status, "value")
                    else str(step_result.status),
                })

            logger.info(f"Nested playbook '{playbook_path}' created {len(nested_screenshots)} screenshots")

            return {
                "playbook": playbook_path,
                "status": "completed",
                "steps_executed": len(nested_results),
                # Return summary of nested steps (nested steps are tracked separately in execution log)
                "steps": nested_results,
                # Track all screenshots created during nested execution (for cleanup on deletion)
                "screenshots": nested_screenshots,
            }

        finally:
            # Remove from execution stack
            self.parent_executor._execution_stack.pop()

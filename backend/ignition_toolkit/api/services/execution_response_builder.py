"""
Execution response builder service

Handles conversion of execution state and database models to API response models.
Extracted from routers/executions.py to reduce router complexity.
"""

import logging
from pathlib import Path

from ignition_toolkit.api.routers.models import ExecutionStatusResponse, StepResultResponse
from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.playbook.models import StepResult
from ignition_toolkit.storage.models import ExecutionModel

logger = logging.getLogger(__name__)


class ExecutionResponseBuilder:
    """
    Service for building execution API responses from various sources

    Centralizes the logic for converting:
    - ExecutionState (in-memory) -> ExecutionStatusResponse (API)
    - ExecutionModel (database) -> ExecutionStatusResponse (API)
    - StepResult (domain) -> StepResultResponse (API)
    """

    @staticmethod
    def convert_step_results_to_response(
        step_results: list[StepResult] | list,
    ) -> list[StepResultResponse]:
        """
        Convert step results to API response format

        Args:
            step_results: List of StepResult domain objects or dicts

        Returns:
            List of StepResultResponse API models
        """
        responses = []
        for result in step_results:
            # Handle both StepResult objects and dict representations
            if isinstance(result, dict):
                responses.append(
                    StepResultResponse(
                        step_id=result.get("step_id", ""),
                        step_name=result.get("step_name", ""),
                        status=result.get("status", "unknown"),
                        output=result.get("output"),
                        error=result.get("error"),
                        started_at=result.get("started_at"),
                        completed_at=result.get("completed_at"),
                        screenshot_path=result.get("screenshot_path"),
                    )
                )
            else:
                responses.append(
                    StepResultResponse(
                        step_id=result.step_id,
                        step_name=result.step_name,
                        status=result.status.value,
                        output=result.output,
                        error=result.error,
                        started_at=result.started_at,
                        completed_at=result.completed_at,
                        screenshot_path=result.screenshot_path,
                    )
                )
        return responses

    @staticmethod
    def from_engine(
        execution_id: str,
        engine: PlaybookEngine,
        playbook_path: Path | None = None,
    ) -> ExecutionStatusResponse:
        """
        Create execution status response from active engine

        Args:
            execution_id: Execution ID
            engine: Active PlaybookEngine instance
            playbook_path: Optional path to playbook file

        Returns:
            ExecutionStatusResponse with current engine state
        """
        execution_state = engine.get_current_execution()

        if not execution_state:
            raise ValueError(f"No execution state found for engine {execution_id}")

        # Determine playbook path from engine or parameter
        final_playbook_path = playbook_path or engine.get_playbook_path()
        playbook_path_str = str(final_playbook_path) if final_playbook_path else None

        return ExecutionStatusResponse(
            execution_id=execution_state.execution_id,
            playbook_name=execution_state.playbook_name,
            status=execution_state.status.value,
            started_at=execution_state.started_at,
            completed_at=execution_state.completed_at,
            total_steps=execution_state.total_steps,
            current_step_index=execution_state.current_step_index,
            step_results=ExecutionResponseBuilder.convert_step_results_to_response(
                execution_state.step_results
            ),
            debug_mode=execution_state.debug_mode,
            error=execution_state.error,
            domain=execution_state.domain,
            playbook_path=playbook_path_str,
            nested_execution_progress=execution_state.nested_execution_progress,
        )

    @staticmethod
    def from_database(db_execution: ExecutionModel) -> ExecutionStatusResponse:
        """
        Create execution status response from database model

        Args:
            db_execution: ExecutionModel from database

        Returns:
            ExecutionStatusResponse with data from database
        """
        # Extract values from execution_metadata (stored as JSON)
        metadata = db_execution.execution_metadata or {}
        total_steps = metadata.get("total_steps", len(db_execution.step_results))
        debug_mode = metadata.get("debug_mode", False)
        domain = metadata.get("domain")

        # Calculate current_step_index from step_results
        # Count completed/failed/skipped steps to determine progress
        completed_count = sum(
            1 for step in db_execution.step_results
            if step.status in ("completed", "failed", "skipped")
        )
        current_step_index = completed_count - 1 if completed_count > 0 else 0

        # Convert step results, extracting screenshot_path from artifacts JSON
        step_results = []
        for step in db_execution.step_results:
            # Extract screenshot_path from artifacts if present
            artifacts = step.artifacts or {}
            screenshot_path = None
            if isinstance(artifacts, dict):
                # Check for single screenshot in artifacts
                screenshot_path = artifacts.get("screenshot_path")
                # Also check for screenshots array
                screenshots = artifacts.get("screenshots", [])
                if screenshots and not screenshot_path:
                    screenshot_path = screenshots[0] if isinstance(screenshots, list) else None

            step_results.append({
                "step_id": step.step_id,
                "step_name": step.step_name,
                "status": step.status,
                "output": step.output,
                "error": step.error_message,  # Note: column is error_message, not error
                "started_at": step.started_at,
                "completed_at": step.completed_at,
                "screenshot_path": screenshot_path,
            })

        return ExecutionStatusResponse(
            execution_id=db_execution.execution_id,
            playbook_name=db_execution.playbook_name,
            status=db_execution.status,
            started_at=db_execution.started_at,
            completed_at=db_execution.completed_at,
            total_steps=total_steps,
            current_step_index=current_step_index,
            step_results=ExecutionResponseBuilder.convert_step_results_to_response(step_results),
            debug_mode=debug_mode,
            error=db_execution.error_message,  # Note: column is error_message, not error
            domain=domain,
            playbook_path=None,  # Not stored in database, only available for active executions
            nested_execution_progress=None,  # Not stored in database, only available for active executions
        )

    @staticmethod
    def from_engine_or_database(
        execution_id: str,
        engine: PlaybookEngine | None,
        db_execution: ExecutionModel | None,
        playbook_path: Path | None = None,
    ) -> ExecutionStatusResponse:
        """
        Create execution status response from engine (if active) or database (if completed)

        Args:
            execution_id: Execution ID
            engine: Active engine (if running)
            db_execution: Database record (if available)
            playbook_path: Optional playbook path

        Returns:
            ExecutionStatusResponse from best available source

        Raises:
            ValueError: If neither engine nor database record is available
        """
        if engine:
            return ExecutionResponseBuilder.from_engine(execution_id, engine, playbook_path)
        elif db_execution:
            return ExecutionResponseBuilder.from_database(db_execution)
        else:
            raise ValueError(f"No execution data found for {execution_id}")

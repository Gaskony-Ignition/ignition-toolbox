"""
Tests for playbook execution engine

Tests execution state management, parameter validation, and control flow.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.playbook.models import (
    ExecutionState,
    ExecutionStatus,
    Playbook,
    PlaybookStep,
    PlaybookParameter,
    StepType,
    StepStatus,
    ParameterType,
    StepResult,
)
from ignition_toolkit.playbook.state_manager import StateManager


class TestPlaybookEngineInit:
    """Test engine initialization"""

    def test_default_initialization(self):
        """Test engine initializes with default values"""
        engine = PlaybookEngine()

        assert engine.gateway_client is None
        assert engine.credential_vault is None
        assert engine.database is None
        assert engine.state_manager is not None
        assert engine.timeout_overrides == {}
        assert engine._current_execution is None
        assert engine._current_playbook is None

    def test_initialization_with_components(self):
        """Test engine initializes with provided components"""
        mock_gateway = MagicMock()
        mock_vault = MagicMock()
        mock_db = MagicMock()
        mock_state = StateManager()
        timeout_overrides = {"gateway_restart": 60}

        engine = PlaybookEngine(
            gateway_client=mock_gateway,
            credential_vault=mock_vault,
            database=mock_db,
            state_manager=mock_state,
            timeout_overrides=timeout_overrides,
        )

        assert engine.gateway_client is mock_gateway
        assert engine.credential_vault is mock_vault
        assert engine.database is mock_db
        assert engine.state_manager is mock_state
        assert engine.timeout_overrides == timeout_overrides


class TestTimeoutConfiguration:
    """Test timeout configuration methods"""

    def test_default_gateway_restart_timeout(self):
        """Test default gateway restart timeout is 120 seconds"""
        engine = PlaybookEngine()
        assert engine.get_gateway_restart_timeout() == 120

    def test_custom_gateway_restart_timeout(self):
        """Test custom gateway restart timeout"""
        engine = PlaybookEngine(timeout_overrides={"gateway_restart": 60})
        assert engine.get_gateway_restart_timeout() == 60

    def test_default_module_install_timeout(self):
        """Test default module install timeout is 300 seconds"""
        engine = PlaybookEngine()
        assert engine.get_module_install_timeout() == 300

    def test_custom_module_install_timeout(self):
        """Test custom module install timeout"""
        engine = PlaybookEngine(timeout_overrides={"module_install": 600})
        assert engine.get_module_install_timeout() == 600

    def test_default_browser_operation_timeout(self):
        """Test default browser operation timeout is 30000 milliseconds"""
        engine = PlaybookEngine()
        assert engine.get_browser_operation_timeout() == 30000

    def test_custom_browser_operation_timeout(self):
        """Test custom browser operation timeout"""
        engine = PlaybookEngine(timeout_overrides={"browser_operation": 60000})
        assert engine.get_browser_operation_timeout() == 60000


class TestUpdateCallback:
    """Test update callback functionality"""

    def test_set_update_callback(self):
        """Test setting update callback"""
        engine = PlaybookEngine()

        def callback(state):
            pass

        engine.set_update_callback(callback)
        assert engine._update_callback is callback


class TestAccessors:
    """Test accessor methods"""

    def test_get_browser_manager_none(self):
        """Test getting browser manager when not initialized"""
        engine = PlaybookEngine()
        assert engine.get_browser_manager() is None

    def test_get_playbook_path_none(self):
        """Test getting playbook path when not executing"""
        engine = PlaybookEngine()
        assert engine.get_playbook_path() is None

    def test_get_current_execution_none(self):
        """Test getting current execution when not executing"""
        engine = PlaybookEngine()
        assert engine.get_current_execution() is None

    def test_get_current_playbook_none(self):
        """Test getting current playbook when not executing"""
        engine = PlaybookEngine()
        assert engine.get_current_playbook() is None


class TestParameterValidation:
    """Test parameter validation logic"""

    def test_validate_required_parameter_missing(self):
        """Test validation fails when required parameter is missing"""
        from ignition_toolkit.playbook.exceptions import PlaybookExecutionError

        engine = PlaybookEngine()

        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            parameters=[
                PlaybookParameter(
                    name="gateway_url",
                    type=ParameterType.STRING,
                    description="Gateway URL",
                    required=True,
                )
            ],
            steps=[],
        )

        # Validation raises PlaybookExecutionError wrapping the ValueError
        with pytest.raises(PlaybookExecutionError, match="gateway_url"):
            engine._validate_parameters(playbook, {})

    def test_validate_required_parameter_present(self):
        """Test validation passes when required parameter is present"""
        engine = PlaybookEngine()

        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            parameters=[
                PlaybookParameter(
                    name="gateway_url",
                    type=ParameterType.STRING,
                    description="Gateway URL",
                    required=True,
                )
            ],
            steps=[],
        )

        # Should not raise
        engine._validate_parameters(playbook, {"gateway_url": "http://localhost:8088"})

    def test_validate_optional_parameter_missing_ok(self):
        """Test validation passes when optional parameter is missing"""
        engine = PlaybookEngine()

        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            parameters=[
                PlaybookParameter(
                    name="timeout",
                    type=ParameterType.INTEGER,
                    description="Timeout",
                    required=False,
                    default=30,
                )
            ],
            steps=[],
        )

        # Should not raise
        engine._validate_parameters(playbook, {})

    def test_validate_unknown_parameter_warning(self):
        """Test validation warns about unknown parameters"""
        engine = PlaybookEngine()

        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            parameters=[],
            steps=[],
        )

        # Should not raise, but logs a warning
        engine._validate_parameters(playbook, {"unknown_param": "value"})


class TestStateManager:
    """Test state manager integration"""

    def test_enable_debug_mode(self):
        """Test enabling debug mode"""
        state_manager = StateManager()
        engine = PlaybookEngine(state_manager=state_manager)

        assert not state_manager.is_debug_mode_enabled()
        engine.enable_debug("test-execution-id")
        assert state_manager.is_debug_mode_enabled()


class TestControlMethods:
    """Test execution control methods"""

    async def test_pause_execution(self):
        """Test pausing execution"""
        state_manager = StateManager()
        engine = PlaybookEngine(state_manager=state_manager)

        await engine.pause()
        assert state_manager.is_paused()

    async def test_resume_execution(self):
        """Test resuming execution"""
        state_manager = StateManager()
        engine = PlaybookEngine(state_manager=state_manager)

        await engine.pause()
        await engine.resume()
        assert not state_manager.is_paused()

    async def test_skip_current_step(self):
        """Test skipping current step"""
        state_manager = StateManager()
        engine = PlaybookEngine(state_manager=state_manager)

        # Skip should set the skip flag
        await engine.skip_current_step()
        assert state_manager.is_skip_requested()

        # Skip flag is consumed on clear
        state_manager.clear_skip()
        assert not state_manager.is_skip_requested()


class TestExecutionStateCreation:
    """Test execution state creation logic"""

    def test_step_result_initialization(self):
        """Test that step results are created with pending status"""
        from ignition_toolkit.playbook.models import StepResult, StepStatus

        # This tests the pattern used in execute_playbook to pre-populate step results
        steps = [
            PlaybookStep(id="step1", name="Step 1", type=StepType.LOG, parameters={"message": "Hello"}),
            PlaybookStep(id="step2", name="Step 2", type=StepType.LOG, parameters={"message": "World"}),
        ]

        # Simulate the step result initialization logic from execute_playbook
        initial_step_results = [
            StepResult(
                step_id=step.id,
                step_name=step.name,
                status=StepStatus.PENDING,
                error=None,
                started_at=None,
                completed_at=None,
            )
            for step in steps
        ]

        assert len(initial_step_results) == 2
        assert all(r.status == StepStatus.PENDING for r in initial_step_results)
        assert initial_step_results[0].step_id == "step1"
        assert initial_step_results[1].step_id == "step2"

    def test_execution_state_fields(self):
        """Test ExecutionState can be created with expected fields"""
        from ignition_toolkit.playbook.models import ExecutionState, ExecutionStatus

        state = ExecutionState(
            execution_id="test-123",
            playbook_name="Test Playbook",
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(),
            total_steps=3,
            debug_mode=False,
            step_results=[],
            domain="gateway",
        )

        assert state.execution_id == "test-123"
        assert state.playbook_name == "Test Playbook"
        assert state.status == ExecutionStatus.RUNNING
        assert state.total_steps == 3
        assert state.domain == "gateway"


class TestCredentialParameterProcessing:
    """Test credential parameter preprocessing"""

    def test_preprocess_credential_parameter(self):
        """Test preprocessing credential-type parameters"""
        mock_vault = MagicMock()
        mock_credential = MagicMock()
        mock_credential.username = "admin"
        mock_credential.password = "password123"
        mock_vault.get_credential.return_value = mock_credential

        engine = PlaybookEngine(credential_vault=mock_vault)

        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            parameters=[
                PlaybookParameter(
                    name="auth_credential",
                    type=ParameterType.CREDENTIAL,
                    description="Authentication credential",
                    required=True,
                )
            ],
            steps=[],
        )

        result = engine._preprocess_credential_parameters(
            playbook, {"auth_credential": "my_cred"}
        )

        # Should replace string with Credential object
        assert result["auth_credential"] is mock_credential
        mock_vault.get_credential.assert_called_once_with("my_cred")

    def test_preprocess_missing_credential_raises_error(self):
        """Test preprocessing raises error when credential not found"""
        from ignition_toolkit.playbook.exceptions import PlaybookExecutionError

        mock_vault = MagicMock()
        mock_vault.get_credential.return_value = None

        engine = PlaybookEngine(credential_vault=mock_vault)

        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            parameters=[
                PlaybookParameter(
                    name="auth_credential",
                    type=ParameterType.CREDENTIAL,
                    description="Authentication credential",
                    required=False,
                )
            ],
            steps=[],
        )

        # Should raise error when credential not found in vault
        with pytest.raises(PlaybookExecutionError, match="not found in vault"):
            engine._preprocess_credential_parameters(
                playbook, {"auth_credential": "nonexistent"}
            )

    def test_preprocess_no_credential_value_skipped(self):
        """Test preprocessing skips credential params with no value"""
        engine = PlaybookEngine()

        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            parameters=[
                PlaybookParameter(
                    name="optional_credential",
                    type=ParameterType.CREDENTIAL,
                    description="Optional credential",
                    required=False,
                )
            ],
            steps=[],
        )

        # When no value is provided and no default, preprocessing should skip it
        result = engine._preprocess_credential_parameters(playbook, {})
        # The parameter should not be in the result since it wasn't provided
        assert "optional_credential" not in result


class TestDomainDetection:
    """Test playbook domain detection for resource setup"""

    def test_gateway_domain_needs_browser(self):
        """Test gateway domain playbooks need browser"""
        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            metadata={"domain": "gateway"},
            parameters=[],
            steps=[
                PlaybookStep(
                    id="step1",
                    name="Step 1",
                    type=StepType.LOG,
                    parameters={"message": "Hello"},
                ),
            ],
        )

        # Check domain detection logic
        has_browser_steps = any(
            step.type.value.startswith("browser.") or step.type.value.startswith("perspective.")
            for step in playbook.steps
        )
        playbook_domain = playbook.metadata.get('domain')
        needs_browser = playbook_domain in ("perspective", "gateway") or has_browser_steps

        assert needs_browser is True

    def test_utility_domain_no_browser(self):
        """Test utility domain playbooks don't need browser"""
        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            metadata={"domain": "utility"},
            parameters=[],
            steps=[
                PlaybookStep(
                    id="step1",
                    name="Step 1",
                    type=StepType.LOG,
                    parameters={"message": "Hello"},
                ),
            ],
        )

        # Check domain detection logic
        has_browser_steps = any(
            step.type.value.startswith("browser.") or step.type.value.startswith("perspective.")
            for step in playbook.steps
        )
        playbook_domain = playbook.metadata.get('domain')
        needs_browser = playbook_domain in ("perspective", "gateway") or has_browser_steps

        assert needs_browser is False

    def test_designer_steps_detected(self):
        """Test designer steps are detected for resource setup"""
        playbook = Playbook(
            name="Test Playbook",
            version="1.0",
            description="Test",
            parameters=[],
            steps=[
                PlaybookStep(
                    id="step1",
                    name="Step 1",
                    type=StepType.DESIGNER_LAUNCH,
                    parameters={},
                ),
            ],
        )

        has_designer_steps = any(step.type.value.startswith("designer.") for step in playbook.steps)
        assert has_designer_steps is True

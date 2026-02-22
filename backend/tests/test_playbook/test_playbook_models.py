"""
Tests for ignition_toolkit/playbook/models.py

Covers: PlaybookStep, Playbook, ExecutionStatus, StepStatus, PlaybookParameter,
        ExecutionState, StepResult dataclasses/enums.
"""

from datetime import datetime

import pytest


class TestExecutionStatus:
    """ExecutionStatus enum has all expected values."""

    def test_pending_value(self):
        from ignition_toolkit.playbook.models import ExecutionStatus

        assert ExecutionStatus.PENDING == "pending"

    def test_running_value(self):
        from ignition_toolkit.playbook.models import ExecutionStatus

        assert ExecutionStatus.RUNNING == "running"

    def test_completed_value(self):
        from ignition_toolkit.playbook.models import ExecutionStatus

        assert ExecutionStatus.COMPLETED == "completed"

    def test_failed_value(self):
        from ignition_toolkit.playbook.models import ExecutionStatus

        assert ExecutionStatus.FAILED == "failed"

    def test_cancelled_value(self):
        from ignition_toolkit.playbook.models import ExecutionStatus

        assert ExecutionStatus.CANCELLED == "cancelled"

    def test_started_value(self):
        from ignition_toolkit.playbook.models import ExecutionStatus

        assert ExecutionStatus.STARTED == "started"

    def test_paused_value(self):
        from ignition_toolkit.playbook.models import ExecutionStatus

        assert ExecutionStatus.PAUSED == "paused"

    def test_is_str_enum(self):
        """ExecutionStatus members should be comparable to plain strings."""
        from ignition_toolkit.playbook.models import ExecutionStatus

        assert ExecutionStatus.COMPLETED == "completed"


class TestStepStatus:
    """StepStatus enum has expected values."""

    def test_pending(self):
        from ignition_toolkit.playbook.models import StepStatus

        assert StepStatus.PENDING == "pending"

    def test_running(self):
        from ignition_toolkit.playbook.models import StepStatus

        assert StepStatus.RUNNING == "running"

    def test_completed(self):
        from ignition_toolkit.playbook.models import StepStatus

        assert StepStatus.COMPLETED == "completed"

    def test_failed(self):
        from ignition_toolkit.playbook.models import StepStatus

        assert StepStatus.FAILED == "failed"

    def test_skipped(self):
        from ignition_toolkit.playbook.models import StepStatus

        assert StepStatus.SKIPPED == "skipped"


class TestPlaybookStep:
    """PlaybookStep dataclass construction and defaults."""

    def test_minimal_construction(self):
        from ignition_toolkit.playbook.models import PlaybookStep, StepType, OnFailureAction

        step = PlaybookStep(
            id="step1",
            name="Login",
            type=StepType.GATEWAY_LOGIN,
        )
        assert step.id == "step1"
        assert step.name == "Login"
        assert step.type == StepType.GATEWAY_LOGIN

    def test_default_on_failure(self):
        from ignition_toolkit.playbook.models import PlaybookStep, StepType, OnFailureAction

        step = PlaybookStep(id="s", name="N", type=StepType.LOG)
        assert step.on_failure == OnFailureAction.ABORT

    def test_default_parameters_empty(self):
        from ignition_toolkit.playbook.models import PlaybookStep, StepType

        step = PlaybookStep(id="s", name="N", type=StepType.LOG)
        assert step.parameters == {}

    def test_custom_parameters(self):
        from ignition_toolkit.playbook.models import PlaybookStep, StepType

        step = PlaybookStep(id="s", name="N", type=StepType.LOG, parameters={"level": "info"})
        assert step.parameters["level"] == "info"

    def test_default_timeout(self):
        from ignition_toolkit.playbook.models import PlaybookStep, StepType

        step = PlaybookStep(id="s", name="N", type=StepType.SLEEP)
        assert step.timeout == 300

    def test_default_retry_count(self):
        from ignition_toolkit.playbook.models import PlaybookStep, StepType

        step = PlaybookStep(id="s", name="N", type=StepType.SLEEP)
        assert step.retry_count == 0


class TestPlaybook:
    """Playbook dataclass construction and helper methods."""

    def test_minimal_construction(self):
        from ignition_toolkit.playbook.models import Playbook

        pb = Playbook(name="My Playbook", version="1.0")
        assert pb.name == "My Playbook"
        assert pb.version == "1.0"

    def test_default_empty_steps(self):
        from ignition_toolkit.playbook.models import Playbook

        pb = Playbook(name="P", version="1.0")
        assert pb.steps == []

    def test_default_empty_parameters(self):
        from ignition_toolkit.playbook.models import Playbook

        pb = Playbook(name="P", version="1.0")
        assert pb.parameters == []

    def test_construction_with_steps(self):
        from ignition_toolkit.playbook.models import Playbook, PlaybookStep, StepType

        step = PlaybookStep(id="s1", name="Log", type=StepType.LOG)
        pb = Playbook(name="P", version="1.0", steps=[step])
        assert len(pb.steps) == 1
        assert pb.steps[0].id == "s1"

    def test_get_step_found(self):
        from ignition_toolkit.playbook.models import Playbook, PlaybookStep, StepType

        step = PlaybookStep(id="step-abc", name="Do it", type=StepType.SLEEP)
        pb = Playbook(name="P", version="1.0", steps=[step])
        assert pb.get_step("step-abc") is step

    def test_get_step_not_found_returns_none(self):
        from ignition_toolkit.playbook.models import Playbook

        pb = Playbook(name="P", version="1.0")
        assert pb.get_step("nonexistent") is None

    def test_get_parameter_found(self):
        from ignition_toolkit.playbook.models import Playbook, PlaybookParameter, ParameterType

        param = PlaybookParameter(name="gateway_url", type=ParameterType.STRING)
        pb = Playbook(name="P", version="1.0", parameters=[param])
        assert pb.get_parameter("gateway_url") is param

    def test_get_parameter_not_found_returns_none(self):
        from ignition_toolkit.playbook.models import Playbook

        pb = Playbook(name="P", version="1.0")
        assert pb.get_parameter("missing") is None


class TestPlaybookParameter:
    """PlaybookParameter dataclass validation."""

    def test_construction(self):
        from ignition_toolkit.playbook.models import PlaybookParameter, ParameterType

        param = PlaybookParameter(name="url", type=ParameterType.STRING)
        assert param.name == "url"
        assert param.type == ParameterType.STRING

    def test_default_required_true(self):
        from ignition_toolkit.playbook.models import PlaybookParameter, ParameterType

        param = PlaybookParameter(name="url", type=ParameterType.STRING)
        assert param.required is True

    def test_validate_string_passes(self):
        from ignition_toolkit.playbook.models import PlaybookParameter, ParameterType

        param = PlaybookParameter(name="url", type=ParameterType.STRING)
        assert param.validate("http://localhost") is True

    def test_validate_wrong_type_raises(self):
        from ignition_toolkit.playbook.models import PlaybookParameter, ParameterType

        param = PlaybookParameter(name="count", type=ParameterType.INTEGER)
        with pytest.raises(ValueError):
            param.validate("not an int")

    def test_validate_required_missing_raises(self):
        from ignition_toolkit.playbook.models import PlaybookParameter, ParameterType

        param = PlaybookParameter(name="url", type=ParameterType.STRING, required=True)
        with pytest.raises(ValueError):
            param.validate(None)


class TestExecutionState:
    """ExecutionState dataclass construction and helper methods."""

    def _make_state(self, **kwargs):
        from ignition_toolkit.playbook.models import ExecutionState, ExecutionStatus

        defaults = dict(
            execution_id="exec-1",
            playbook_name="My Playbook",
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        defaults.update(kwargs)
        return ExecutionState(**defaults)

    def test_construction(self):
        state = self._make_state()
        assert state.execution_id == "exec-1"

    def test_default_step_results_empty(self):
        state = self._make_state()
        assert state.step_results == []

    def test_get_step_result_not_found(self):
        state = self._make_state()
        assert state.get_step_result("missing") is None

    def test_add_and_get_step_result(self):
        from ignition_toolkit.playbook.models import StepResult, StepStatus

        state = self._make_state()
        result = StepResult(
            step_id="s1",
            step_name="Step One",
            status=StepStatus.COMPLETED,
            started_at=datetime.now(),
        )
        state.add_step_result(result)
        assert state.get_step_result("s1") is result

    def test_add_step_result_updates_existing(self):
        from ignition_toolkit.playbook.models import StepResult, StepStatus

        state = self._make_state()
        r1 = StepResult(step_id="s1", step_name="S1", status=StepStatus.RUNNING, started_at=datetime.now())
        r2 = StepResult(step_id="s1", step_name="S1", status=StepStatus.COMPLETED, started_at=datetime.now())

        state.add_step_result(r1)
        state.add_step_result(r2)

        # Should not duplicate
        assert len(state.step_results) == 1
        assert state.get_step_result("s1").status == StepStatus.COMPLETED

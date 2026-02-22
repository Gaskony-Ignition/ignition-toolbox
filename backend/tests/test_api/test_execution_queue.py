"""
Tests for execution queue API endpoints.

Tests queue status, enqueue, cancel, running list, parallel execution,
and resource management endpoints.
Uses direct function calls with mocking (same pattern as test_health.py).
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_queued_execution(execution_id: str = "exec-001", priority: str = "NORMAL") -> MagicMock:
    """Return a mock QueuedExecution object."""
    exec_mock = MagicMock()
    exec_mock.id = execution_id
    exec_mock.playbook_path = "playbooks/test.yaml"
    exec_mock.priority = MagicMock()
    exec_mock.priority.name = priority
    exec_mock.to_dict.return_value = {
        "id": execution_id,
        "playbook_path": "playbooks/test.yaml",
        "priority": priority,
        "state": "queued",
    }
    return exec_mock


def _make_queue_mock(
    status: dict | None = None,
    running: list | None = None,
    enqueue_result=None,
    cancel_result: bool = True,
) -> MagicMock:
    """Build a mock ExecutionQueue."""
    queue = MagicMock()
    queue.get_status.return_value = status or {
        "queued": 0,
        "running": 0,
        "available_slots": 5,
        "max_concurrent": 5,
    }
    queue.get_running.return_value = running or []
    queue.enqueue = AsyncMock(return_value=enqueue_result or _make_queued_execution())
    queue.cancel = AsyncMock(return_value=cancel_result)
    return queue


def _make_parallel_manager_mock(status: dict | None = None, cancel_result: bool = True) -> MagicMock:
    """Build a mock ParallelExecutionManager."""
    manager = MagicMock()
    manager.get_status.return_value = status or {"running": 0, "max_parallel": 10}
    manager.run_parallel = AsyncMock(return_value={"results": [], "total": 0, "succeeded": 0, "failed": 0})
    manager.cancel = AsyncMock(return_value=cancel_result)
    return manager


def _make_resource_limiter_mock(status: dict | None = None) -> MagicMock:
    """Build a mock ResourceLimiter."""
    limiter = MagicMock()
    limiter.get_status.return_value = status or {
        "browser": {"limit": 5, "available": 5},
        "gateway": {"limit": 10, "available": 10},
    }
    limiter.set_limit.return_value = None
    return limiter


# ---------------------------------------------------------------------------
# get_queue_status
# ---------------------------------------------------------------------------

class TestGetQueueStatus:
    def test_get_queue_status_returns_dict(self):
        """GET /execution-queue/status returns queue status dictionary."""
        from ignition_toolkit.api.routers.execution_queue import get_queue_status

        mock_queue = _make_queue_mock(status={
            "queued": 2,
            "running": 1,
            "available_slots": 4,
            "max_concurrent": 5,
        })

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            result = asyncio.run(get_queue_status())

        assert isinstance(result, dict)
        assert result["queued"] == 2
        assert result["running"] == 1
        assert result["available_slots"] == 4

    def test_get_queue_status_empty_queue(self):
        """GET /execution-queue/status returns zeros for empty queue."""
        from ignition_toolkit.api.routers.execution_queue import get_queue_status

        mock_queue = _make_queue_mock(status={"queued": 0, "running": 0, "available_slots": 5})

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            result = asyncio.run(get_queue_status())

        assert result["queued"] == 0
        assert result["running"] == 0

    def test_get_queue_status_calls_get_status(self):
        """GET /execution-queue/status delegates to queue.get_status()."""
        from ignition_toolkit.api.routers.execution_queue import get_queue_status

        mock_queue = _make_queue_mock()

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            asyncio.run(get_queue_status())

        mock_queue.get_status.assert_called_once()


# ---------------------------------------------------------------------------
# enqueue_execution
# ---------------------------------------------------------------------------

class TestEnqueueExecution:
    def test_enqueue_returns_success_and_execution(self):
        """POST /execution-queue/enqueue returns success and execution dict."""
        from ignition_toolkit.api.routers.execution_queue import enqueue_execution, EnqueueRequest

        queued_exec = _make_queued_execution("new-exec-001", "NORMAL")
        mock_queue = _make_queue_mock(enqueue_result=queued_exec)

        request = EnqueueRequest(
            playbook_path="playbooks/test.yaml",
            priority="normal",
        )

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            result = asyncio.run(enqueue_execution(request))

        assert result["success"] is True
        assert "execution" in result
        assert result["execution"]["id"] == "new-exec-001"

    def test_enqueue_high_priority(self):
        """POST /execution-queue/enqueue with priority=high passes HIGH enum to queue."""
        from ignition_toolkit.api.routers.execution_queue import enqueue_execution, EnqueueRequest
        from ignition_toolkit.execution import ExecutionPriority

        queued_exec = _make_queued_execution("hp-exec", "HIGH")
        mock_queue = _make_queue_mock(enqueue_result=queued_exec)

        request = EnqueueRequest(
            playbook_path="playbooks/test.yaml",
            priority="high",
        )

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            result = asyncio.run(enqueue_execution(request))

        call_kwargs = mock_queue.enqueue.call_args.kwargs
        assert call_kwargs["priority"] == ExecutionPriority.HIGH

    def test_enqueue_low_priority(self):
        """POST /execution-queue/enqueue with priority=low passes LOW enum to queue."""
        from ignition_toolkit.api.routers.execution_queue import enqueue_execution, EnqueueRequest
        from ignition_toolkit.execution import ExecutionPriority

        queued_exec = _make_queued_execution("lp-exec", "LOW")
        mock_queue = _make_queue_mock(enqueue_result=queued_exec)

        request = EnqueueRequest(
            playbook_path="playbooks/test.yaml",
            priority="low",
        )

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            result = asyncio.run(enqueue_execution(request))

        call_kwargs = mock_queue.enqueue.call_args.kwargs
        assert call_kwargs["priority"] == ExecutionPriority.LOW

    def test_enqueue_unknown_priority_defaults_to_normal(self):
        """POST /execution-queue/enqueue with unrecognised priority falls back to NORMAL."""
        from ignition_toolkit.api.routers.execution_queue import enqueue_execution, EnqueueRequest
        from ignition_toolkit.execution import ExecutionPriority

        queued_exec = _make_queued_execution()
        mock_queue = _make_queue_mock(enqueue_result=queued_exec)

        request = EnqueueRequest(
            playbook_path="playbooks/test.yaml",
            priority="urgent",  # Not in the priority_map
        )

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            result = asyncio.run(enqueue_execution(request))

        call_kwargs = mock_queue.enqueue.call_args.kwargs
        assert call_kwargs["priority"] == ExecutionPriority.NORMAL

    def test_enqueue_passes_parameters_and_credentials(self):
        """POST /execution-queue/enqueue forwards optional fields to queue."""
        from ignition_toolkit.api.routers.execution_queue import enqueue_execution, EnqueueRequest

        queued_exec = _make_queued_execution()
        mock_queue = _make_queue_mock(enqueue_result=queued_exec)

        request = EnqueueRequest(
            playbook_path="playbooks/with_params.yaml",
            parameters={"env": "staging"},
            gateway_url="http://gateway:8088",
            credential_name="prod-creds",
            priority="normal",
        )

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            asyncio.run(enqueue_execution(request))

        call_kwargs = mock_queue.enqueue.call_args.kwargs
        assert call_kwargs["parameters"] == {"env": "staging"}
        assert call_kwargs["gateway_url"] == "http://gateway:8088"
        assert call_kwargs["credential_name"] == "prod-creds"

    def test_enqueue_playbook_path_required(self):
        """EnqueueRequest requires playbook_path; omitting raises ValidationError."""
        from ignition_toolkit.api.routers.execution_queue import EnqueueRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EnqueueRequest()  # missing required playbook_path


# ---------------------------------------------------------------------------
# cancel_queued_execution
# ---------------------------------------------------------------------------

class TestCancelQueuedExecution:
    def test_cancel_queued_execution_success(self):
        """DELETE /execution-queue/cancel/{id} returns success when cancelled."""
        from ignition_toolkit.api.routers.execution_queue import cancel_queued_execution

        mock_queue = _make_queue_mock(cancel_result=True)

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            result = asyncio.run(cancel_queued_execution("exec-001"))

        assert result["success"] is True
        mock_queue.cancel.assert_awaited_once_with("exec-001")

    def test_cancel_queued_execution_404_when_not_found(self):
        """DELETE /execution-queue/cancel/{id} raises 404 when execution not found."""
        from ignition_toolkit.api.routers.execution_queue import cancel_queued_execution

        mock_queue = _make_queue_mock(cancel_result=False)

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(cancel_queued_execution("nonexistent-exec"))

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_running_executions
# ---------------------------------------------------------------------------

class TestGetRunningExecutions:
    def test_get_running_returns_list(self):
        """GET /execution-queue/running returns running executions list."""
        from ignition_toolkit.api.routers.execution_queue import get_running_executions

        running_exec = _make_queued_execution("run-exec-001", "HIGH")
        mock_queue = _make_queue_mock(running=[running_exec])

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            result = asyncio.run(get_running_executions())

        assert "running" in result
        assert "count" in result
        assert result["count"] == 1
        assert result["running"][0]["id"] == "run-exec-001"

    def test_get_running_empty_when_no_executions(self):
        """GET /execution-queue/running returns empty list when nothing is running."""
        from ignition_toolkit.api.routers.execution_queue import get_running_executions

        mock_queue = _make_queue_mock(running=[])

        with patch("ignition_toolkit.api.routers.execution_queue.get_execution_queue", return_value=mock_queue):
            result = asyncio.run(get_running_executions())

        assert result["running"] == []
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# run_parallel_executions
# ---------------------------------------------------------------------------

class TestRunParallelExecutions:
    def test_run_parallel_returns_results(self):
        """POST /execution-queue/parallel runs playbooks and returns results dict."""
        from ignition_toolkit.api.routers.execution_queue import run_parallel_executions, ParallelExecutionRequest

        mock_manager = _make_parallel_manager_mock()

        request = ParallelExecutionRequest(
            playbooks=[
                {"playbook_path": "playbooks/a.yaml"},
                {"playbook_path": "playbooks/b.yaml"},
            ]
        )

        with patch("ignition_toolkit.api.routers.execution_queue.get_parallel_manager", return_value=mock_manager):
            result = asyncio.run(run_parallel_executions(request))

        assert "results" in result
        mock_manager.run_parallel.assert_awaited_once()

    def test_run_parallel_400_for_empty_playbooks(self):
        """POST /execution-queue/parallel raises 400 when playbooks list is empty."""
        from ignition_toolkit.api.routers.execution_queue import run_parallel_executions, ParallelExecutionRequest

        mock_manager = _make_parallel_manager_mock()

        request = ParallelExecutionRequest(playbooks=[])

        with patch("ignition_toolkit.api.routers.execution_queue.get_parallel_manager", return_value=mock_manager):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(run_parallel_executions(request))

        assert exc_info.value.status_code == 400

    def test_run_parallel_400_for_too_many_playbooks(self):
        """POST /execution-queue/parallel raises 400 when more than 20 playbooks provided."""
        from ignition_toolkit.api.routers.execution_queue import run_parallel_executions, ParallelExecutionRequest

        mock_manager = _make_parallel_manager_mock()

        # 21 playbooks - exceeds limit
        playbooks = [{"playbook_path": f"playbooks/{i}.yaml"} for i in range(21)]
        request = ParallelExecutionRequest(playbooks=playbooks)

        with patch("ignition_toolkit.api.routers.execution_queue.get_parallel_manager", return_value=mock_manager):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(run_parallel_executions(request))

        assert exc_info.value.status_code == 400

    def test_run_parallel_at_limit_succeeds(self):
        """POST /execution-queue/parallel accepts exactly 20 playbooks."""
        from ignition_toolkit.api.routers.execution_queue import run_parallel_executions, ParallelExecutionRequest

        mock_manager = _make_parallel_manager_mock()

        playbooks = [{"playbook_path": f"playbooks/{i}.yaml"} for i in range(20)]
        request = ParallelExecutionRequest(playbooks=playbooks)

        with patch("ignition_toolkit.api.routers.execution_queue.get_parallel_manager", return_value=mock_manager):
            result = asyncio.run(run_parallel_executions(request))

        assert "results" in result


# ---------------------------------------------------------------------------
# get_parallel_execution_status
# ---------------------------------------------------------------------------

class TestGetParallelExecutionStatus:
    def test_get_parallel_status_returns_dict(self):
        """GET /execution-queue/parallel/status returns status dictionary."""
        from ignition_toolkit.api.routers.execution_queue import get_parallel_execution_status

        status = {"running": 2, "max_parallel": 10, "completed_today": 5}
        mock_manager = _make_parallel_manager_mock(status=status)

        with patch("ignition_toolkit.api.routers.execution_queue.get_parallel_manager", return_value=mock_manager):
            result = asyncio.run(get_parallel_execution_status())

        assert result["running"] == 2
        assert result["max_parallel"] == 10


# ---------------------------------------------------------------------------
# cancel_parallel_execution
# ---------------------------------------------------------------------------

class TestCancelParallelExecution:
    def test_cancel_parallel_succeeds(self):
        """DELETE /execution-queue/parallel/cancel/{id} returns success."""
        from ignition_toolkit.api.routers.execution_queue import cancel_parallel_execution

        mock_manager = _make_parallel_manager_mock(cancel_result=True)

        with patch("ignition_toolkit.api.routers.execution_queue.get_parallel_manager", return_value=mock_manager):
            result = asyncio.run(cancel_parallel_execution("par-exec-001"))

        assert result["success"] is True
        mock_manager.cancel.assert_awaited_once_with("par-exec-001")

    def test_cancel_parallel_404_when_not_found(self):
        """DELETE /execution-queue/parallel/cancel/{id} raises 404 when not found."""
        from ignition_toolkit.api.routers.execution_queue import cancel_parallel_execution

        mock_manager = _make_parallel_manager_mock(cancel_result=False)

        with patch("ignition_toolkit.api.routers.execution_queue.get_parallel_manager", return_value=mock_manager):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(cancel_parallel_execution("nonexistent"))

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_resource_status
# ---------------------------------------------------------------------------

class TestGetResourceStatus:
    def test_get_resource_status_returns_dict(self):
        """GET /execution-queue/resources returns resource status."""
        from ignition_toolkit.api.routers.execution_queue import get_resource_status

        status = {
            "browser": {"limit": 5, "available": 3},
            "gateway": {"limit": 10, "available": 10},
            "memory": {"limit": 8, "available": 8},
            "cpu": {"limit": 4, "available": 2},
        }
        mock_limiter = _make_resource_limiter_mock(status=status)

        with patch("ignition_toolkit.api.routers.execution_queue.get_resource_limiter", return_value=mock_limiter):
            result = asyncio.run(get_resource_status())

        assert "browser" in result
        assert result["browser"]["limit"] == 5
        assert result["browser"]["available"] == 3

    def test_get_resource_status_calls_get_status(self):
        """GET /execution-queue/resources delegates to limiter.get_status()."""
        from ignition_toolkit.api.routers.execution_queue import get_resource_status

        mock_limiter = _make_resource_limiter_mock()

        with patch("ignition_toolkit.api.routers.execution_queue.get_resource_limiter", return_value=mock_limiter):
            asyncio.run(get_resource_status())

        mock_limiter.get_status.assert_called_once()


# ---------------------------------------------------------------------------
# update_resource_limits
# ---------------------------------------------------------------------------

class TestUpdateResourceLimits:
    def test_update_resource_limits_success(self):
        """PUT /execution-queue/resources/limits updates specified limits and returns status."""
        from ignition_toolkit.api.routers.execution_queue import update_resource_limits, ResourceLimitUpdate
        from ignition_toolkit.execution import ResourceType

        mock_limiter = _make_resource_limiter_mock()

        request = ResourceLimitUpdate(browser_limit=3, gateway_limit=8)

        with patch("ignition_toolkit.api.routers.execution_queue.get_resource_limiter", return_value=mock_limiter):
            result = asyncio.run(update_resource_limits(request))

        assert result["success"] is True
        assert "status" in result
        # Verify set_limit was called for each provided resource
        calls = [call.args for call in mock_limiter.set_limit.call_args_list]
        call_types = [c[0] for c in calls]
        assert ResourceType.BROWSER in call_types
        assert ResourceType.GATEWAY in call_types

    def test_update_resource_limits_only_updates_provided_fields(self):
        """PUT /execution-queue/resources/limits only calls set_limit for non-None fields."""
        from ignition_toolkit.api.routers.execution_queue import update_resource_limits, ResourceLimitUpdate
        from ignition_toolkit.execution import ResourceType

        mock_limiter = _make_resource_limiter_mock()

        # Only provide browser_limit — others should be skipped
        request = ResourceLimitUpdate(browser_limit=2)

        with patch("ignition_toolkit.api.routers.execution_queue.get_resource_limiter", return_value=mock_limiter):
            asyncio.run(update_resource_limits(request))

        call_types = [call.args[0] for call in mock_limiter.set_limit.call_args_list]
        assert ResourceType.BROWSER in call_types
        assert ResourceType.GATEWAY not in call_types
        assert ResourceType.MEMORY not in call_types
        assert ResourceType.CPU not in call_types

    def test_update_resource_limits_validation_browser_range(self):
        """ResourceLimitUpdate validates browser_limit is 1-20."""
        from ignition_toolkit.api.routers.execution_queue import ResourceLimitUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ResourceLimitUpdate(browser_limit=0)

        with pytest.raises(ValidationError):
            ResourceLimitUpdate(browser_limit=21)

        valid = ResourceLimitUpdate(browser_limit=1)
        assert valid.browser_limit == 1

        valid_max = ResourceLimitUpdate(browser_limit=20)
        assert valid_max.browser_limit == 20

    def test_update_resource_limits_validation_gateway_range(self):
        """ResourceLimitUpdate validates gateway_limit is 1-50."""
        from ignition_toolkit.api.routers.execution_queue import ResourceLimitUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ResourceLimitUpdate(gateway_limit=0)

        with pytest.raises(ValidationError):
            ResourceLimitUpdate(gateway_limit=51)

        valid = ResourceLimitUpdate(gateway_limit=50)
        assert valid.gateway_limit == 50

    def test_update_resource_limits_validation_cpu_range(self):
        """ResourceLimitUpdate validates cpu_limit is 1-16."""
        from ignition_toolkit.api.routers.execution_queue import ResourceLimitUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ResourceLimitUpdate(cpu_limit=17)

        valid = ResourceLimitUpdate(cpu_limit=16)
        assert valid.cpu_limit == 16

    def test_update_resource_limits_all_none_is_valid(self):
        """ResourceLimitUpdate with all None fields is valid (no-op update)."""
        from ignition_toolkit.api.routers.execution_queue import ResourceLimitUpdate

        req = ResourceLimitUpdate()
        assert req.browser_limit is None
        assert req.gateway_limit is None
        assert req.memory_limit is None
        assert req.cpu_limit is None


# ---------------------------------------------------------------------------
# QueueSettingsUpdate model validation
# ---------------------------------------------------------------------------

class TestQueueSettingsUpdateModel:
    def test_max_concurrent_range(self):
        """QueueSettingsUpdate validates max_concurrent is 1-20."""
        from ignition_toolkit.api.routers.execution_queue import QueueSettingsUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            QueueSettingsUpdate(max_concurrent=0)

        with pytest.raises(ValidationError):
            QueueSettingsUpdate(max_concurrent=21)

        valid = QueueSettingsUpdate(max_concurrent=5)
        assert valid.max_concurrent == 5

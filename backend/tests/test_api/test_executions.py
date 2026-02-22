"""
Tests for execution management API endpoints.

Tests list, get, cancel, pause, resume, and skip operations.
Uses direct function calls with mocking (same pattern as test_health.py).
"""

import asyncio
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_db():
    """Create a mock database that returns no results for all queries."""
    db = MagicMock()
    mock_session = MagicMock()
    mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.filter_by.return_value.first.return_value = None

    @contextmanager
    def session_scope():
        yield mock_session

    db.session_scope = session_scope
    return db


@pytest.fixture
def mock_services():
    """Set up mock app.state.services so service-layer endpoints work."""
    from ignition_toolkit.api.app import app

    svc = MagicMock()
    svc.execution_manager.get_engine.return_value = None
    svc.execution_manager.cancel_execution = AsyncMock(return_value=None)
    app.state.services = svc
    yield svc
    try:
        del app.state.services
    except AttributeError:
        pass


class TestListExecutions:
    def test_list_executions_returns_list(self, mock_db):
        """GET /api/executions returns a list (empty when no executions exist)."""
        from ignition_toolkit.api.routers.executions.main import list_executions

        with patch(
            "ignition_toolkit.api.routers.executions.main.get_active_engines",
            return_value={},
        ), patch(
            "ignition_toolkit.api.routers.executions.main.get_database",
            return_value=mock_db,
        ):
            result = asyncio.run(list_executions())

        assert isinstance(result, list)


class TestGetExecution:
    def test_get_execution_404_for_unknown_id(self, mock_db):
        """GET /api/executions/{id} returns 404 for an unknown execution id."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.executions.main import get_execution_status

        with patch(
            "ignition_toolkit.api.routers.executions.main.get_active_engines",
            return_value={},
        ), patch(
            "ignition_toolkit.api.routers.executions.main.get_database",
            return_value=mock_db,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_execution_status("nonexistent-execution-id"))

        assert exc_info.value.status_code == 404


class TestPauseExecution:
    def test_pause_404_for_unknown_id(self, mock_services):
        """POST /api/executions/{id}/pause returns 404 for unknown execution."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.executions.helpers import get_engine_or_404

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_engine_or_404("nonexistent-id"))

        assert exc_info.value.status_code == 404


class TestResumeExecution:
    def test_resume_404_for_unknown_id(self, mock_services):
        """POST /api/executions/{id}/resume returns 404 for unknown execution."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.executions.helpers import get_engine_or_404

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_engine_or_404("nonexistent-id"))

        assert exc_info.value.status_code == 404


class TestSkipStep:
    def test_skip_404_for_unknown_id(self, mock_services):
        """POST /api/executions/{id}/skip returns 404 for unknown execution."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.executions.helpers import get_engine_or_404

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_engine_or_404("nonexistent-id"))

        assert exc_info.value.status_code == 404


class TestCancelExecution:
    def test_cancel_404_for_unknown_id(self, mock_services, mock_db):
        """POST /api/executions/{id}/cancel returns 404 for a completely unknown execution id."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.executions.main import cancel_execution

        with patch(
            "ignition_toolkit.api.routers.executions.main.get_database",
            return_value=mock_db,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(cancel_execution("nonexistent-execution-id"))

        assert exc_info.value.status_code == 404

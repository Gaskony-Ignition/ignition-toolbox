"""
Tests for context API endpoints.

Tests the /api/context/summary and /api/context/full endpoints, verifying they
return well-structured responses and handle empty databases gracefully.

All external dependencies (database, CredentialVault, CloudDesigner, log capture,
playbook loader, active_engines) are mocked so no real I/O happens.
"""

import asyncio
import pytest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


# ---------------------------------------------------------------------------
# Shared mock builders
# ---------------------------------------------------------------------------


def _make_mock_db(executions=None):
    """Return a mock database whose session returns the given executions list."""
    db = MagicMock()
    session = MagicMock()

    # Default to no executions
    rows = executions if executions is not None else []
    session.query.return_value.order_by.return_value.limit.return_value.all.return_value = rows
    session.query.return_value.filter.return_value.first.return_value = None

    @contextmanager
    def session_scope():
        yield session

    db.session_scope = session_scope
    db._session = session
    return db


def _make_mock_vault(credentials=None):
    """Return a mock CredentialVault with the given list of credentials."""
    vault = MagicMock()
    vault.list_credentials.return_value = credentials if credentials is not None else []
    return vault


def _mock_clouddesigner_status(status="stopped", port=None):
    """Return a mock CloudDesigner status object."""
    s = MagicMock()
    s.status = status
    s.port = port
    return s


def _make_patch_stack(
    *,
    db=None,
    vault_creds=None,
    cloud_status="stopped",
    cloud_port=None,
    playbooks_dir_exists=False,
    log_capture=None,
):
    """
    Build a dict of patch targets with sensible defaults.

    Returns a list of (target, mock) tuples ready for use with patch().
    """
    mock_db = db or _make_mock_db()
    mock_vault = _make_mock_vault(vault_creds)
    cloud_stat = _mock_clouddesigner_status(cloud_status, cloud_port)

    mock_manager = MagicMock()
    mock_manager.get_container_status.return_value = cloud_stat

    # Playbooks directory — non-existent by default so no YAML loading happens
    mock_pb_dir = MagicMock(spec=Path)
    mock_pb_dir.exists.return_value = playbooks_dir_exists
    if not playbooks_dir_exists:
        mock_pb_dir.rglob.return_value = []

    return {
        "db": mock_db,
        "vault": mock_vault,
        "manager": mock_manager,
        "pb_dir": mock_pb_dir,
        "log_capture": log_capture,
    }


# ---------------------------------------------------------------------------
# Fixture: apply all patches for the context router
# ---------------------------------------------------------------------------


def _run_summary(mocks):
    """Run get_context_summary() with the given mock objects applied."""
    from ignition_toolkit.api.routers.context import get_context_summary

    with patch(
        "ignition_toolkit.api.routers.context.get_database", return_value=mocks["db"]
    ), patch(
        "ignition_toolkit.api.routers.context.CredentialVault", return_value=mocks["vault"]
    ), patch(
        "ignition_toolkit.clouddesigner.manager.get_clouddesigner_manager",
        return_value=mocks["manager"],
    ), patch(
        "ignition_toolkit.api.routers.context.get_log_capture",
        return_value=mocks["log_capture"],
    ), patch(
        # get_playbooks_dir is imported locally inside _get_playbooks_summary()
        "ignition_toolkit.core.paths.get_playbooks_dir",
        return_value=mocks["pb_dir"],
    ), patch(
        # active_engines is imported locally inside _get_system_summary()
        "ignition_toolkit.api.app.active_engines", {}
    ):
        return asyncio.run(get_context_summary())


def _run_full(mocks, **kwargs):
    """Run get_full_context() with the given mock objects applied."""
    from ignition_toolkit.api.routers.context import get_full_context

    with patch(
        "ignition_toolkit.api.routers.context.get_database", return_value=mocks["db"]
    ), patch(
        "ignition_toolkit.api.routers.context.CredentialVault", return_value=mocks["vault"]
    ), patch(
        "ignition_toolkit.clouddesigner.manager.get_clouddesigner_manager",
        return_value=mocks["manager"],
    ), patch(
        "ignition_toolkit.api.routers.context.get_log_capture",
        return_value=mocks["log_capture"],
    ), patch(
        "ignition_toolkit.core.paths.get_playbooks_dir",
        return_value=mocks["pb_dir"],
    ), patch(
        "ignition_toolkit.api.app.active_engines", {}
    ):
        return asyncio.run(get_full_context(**kwargs))


# ---------------------------------------------------------------------------
# get_context_summary tests
# ---------------------------------------------------------------------------


class TestGetContextSummary:
    """Tests for GET /api/context/summary"""

    def test_returns_dict(self):
        """get_context_summary() must return a ContextSummaryResponse-like object."""
        from ignition_toolkit.api.routers.context import ContextSummaryResponse

        mocks = _make_patch_stack()
        result = _run_summary(mocks)

        assert isinstance(result, ContextSummaryResponse)

    def test_top_level_keys_present(self):
        """The response must contain all expected top-level attributes."""
        mocks = _make_patch_stack()
        result = _run_summary(mocks)

        assert hasattr(result, "playbooks")
        assert hasattr(result, "recent_executions")
        assert hasattr(result, "credentials")
        assert hasattr(result, "clouddesigner")
        assert hasattr(result, "system")
        assert hasattr(result, "recent_logs")

    def test_playbooks_is_empty_list_when_dir_does_not_exist(self):
        """When the playbooks directory does not exist, playbooks must be []."""
        mocks = _make_patch_stack(playbooks_dir_exists=False)
        result = _run_summary(mocks)

        assert result.playbooks == []

    def test_recent_executions_is_empty_list_when_db_returns_no_rows(self):
        """When the DB returns no executions, recent_executions must be []."""
        mocks = _make_patch_stack()
        result = _run_summary(mocks)

        assert result.recent_executions == []

    def test_credentials_is_empty_list_when_vault_is_empty(self):
        """When the vault has no credentials, credentials must be []."""
        mocks = _make_patch_stack(vault_creds=[])
        result = _run_summary(mocks)

        assert result.credentials == []

    def test_clouddesigner_status_reflects_mock(self):
        """The clouddesigner status must match the mock manager's return value."""
        mocks = _make_patch_stack(cloud_status="running", cloud_port=8087)
        result = _run_summary(mocks)

        assert result.clouddesigner.status == "running"
        assert result.clouddesigner.port == 8087

    def test_clouddesigner_unknown_when_manager_raises(self):
        """When the CloudDesigner manager raises, clouddesigner.status must be 'unknown'."""
        mocks = _make_patch_stack()
        mocks["manager"].get_container_status.side_effect = RuntimeError("Docker not running")

        result = _run_summary(mocks)

        assert result.clouddesigner.status == "unknown"

    def test_system_active_executions_is_zero_when_dict_is_empty(self):
        """With no active engines, system.active_executions must be 0."""
        mocks = _make_patch_stack()
        result = _run_summary(mocks)

        assert result.system.active_executions == 0

    def test_recent_logs_is_empty_list_when_log_capture_is_none(self):
        """When get_log_capture() returns None, recent_logs must be []."""
        mocks = _make_patch_stack(log_capture=None)
        result = _run_summary(mocks)

        assert result.recent_logs == []

    def test_recent_logs_is_empty_when_capture_returns_empty(self):
        """When log capture returns zero entries, recent_logs must be []."""
        mock_capture = MagicMock()
        mock_capture.get_logs.return_value = []

        mocks = _make_patch_stack(log_capture=mock_capture)
        result = _run_summary(mocks)

        assert result.recent_logs == []

    def test_credentials_names_match_vault_entries(self):
        """Credential summaries must list credential names from the vault."""
        from ignition_toolkit.credentials.models import Credential

        stored = [
            Credential(name="cred-x", username="u1", password="<enc>"),
            Credential(name="cred-y", username="u2", password="<enc>", gateway_url="http://gw"),
        ]
        mocks = _make_patch_stack(vault_creds=stored)
        result = _run_summary(mocks)

        names = {c.name for c in result.credentials}
        assert names == {"cred-x", "cred-y"}

    def test_credentials_has_gateway_url_flag(self):
        """Credentials with a gateway_url must have has_gateway_url=True."""
        from ignition_toolkit.credentials.models import Credential

        stored = [
            Credential(name="with-gw", username="u", password="p", gateway_url="http://gw:8088"),
            Credential(name="no-gw", username="u", password="p", gateway_url=None),
        ]
        mocks = _make_patch_stack(vault_creds=stored)
        result = _run_summary(mocks)

        by_name = {c.name: c for c in result.credentials}
        assert by_name["with-gw"].has_gateway_url is True
        assert by_name["no-gw"].has_gateway_url is False


# ---------------------------------------------------------------------------
# get_full_context tests
# ---------------------------------------------------------------------------


class TestGetFullContext:
    """Tests for GET /api/context/full"""

    def test_returns_full_context_response(self):
        """get_full_context() must return a FullContextResponse-like object."""
        from ignition_toolkit.api.routers.context import FullContextResponse

        mocks = _make_patch_stack()
        result = _run_full(mocks)

        assert isinstance(result, FullContextResponse)

    def test_top_level_keys_present(self):
        """The full context response must contain all expected attributes."""
        mocks = _make_patch_stack()
        result = _run_full(mocks)

        assert hasattr(result, "playbooks")
        assert hasattr(result, "executions")
        assert hasattr(result, "credentials")
        assert hasattr(result, "clouddesigner")
        assert hasattr(result, "system")
        assert hasattr(result, "logs")
        assert hasattr(result, "error_logs")

    def test_empty_database_returns_empty_executions(self):
        """When the DB is empty, executions must be []."""
        mocks = _make_patch_stack()
        result = _run_full(mocks)

        assert result.executions == []

    def test_logs_is_empty_list_when_capture_is_none(self):
        """When log capture is None, logs and error_logs must both be []."""
        mocks = _make_patch_stack(log_capture=None)
        result = _run_full(mocks)

        assert result.logs == []
        assert result.error_logs == []

    def test_get_full_context_accepts_execution_and_log_limits(self):
        """get_full_context() must accept execution_limit and log_limit query params."""
        mocks = _make_patch_stack()
        # Should not raise; the function accepts these keyword arguments
        result = _run_full(mocks, execution_limit=5, log_limit=50)

        assert isinstance(result.executions, list)
        assert isinstance(result.logs, list)

    def test_clouddesigner_stopped_by_default(self):
        """With the default mock, clouddesigner.status must be 'stopped'."""
        mocks = _make_patch_stack(cloud_status="stopped")
        result = _run_full(mocks)

        assert result.clouddesigner.status == "stopped"


# ---------------------------------------------------------------------------
# get_execution_context tests
# ---------------------------------------------------------------------------


class TestGetExecutionContext:
    """Tests for GET /api/context/execution/{execution_id}"""

    def test_returns_404_for_unknown_execution(self, mock_db):
        """When the execution is not in the DB, HTTP 404 must be raised."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.context import get_execution_context

        with patch(
            "ignition_toolkit.api.routers.context.get_database", return_value=mock_db
        ), patch(
            "ignition_toolkit.api.routers.context.get_log_capture", return_value=None
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_execution_context("nonexistent-execution-id"))

        assert exc_info.value.status_code == 404

    def test_returns_503_when_database_is_none(self):
        """When get_database() returns None, HTTP 503 must be raised."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.context import get_execution_context

        with patch("ignition_toolkit.api.routers.context.get_database", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_execution_context("any-id"))

        assert exc_info.value.status_code == 503

    def test_returns_execution_and_logs_for_known_execution(self, mock_db):
        """When the execution exists in the DB, response must contain 'execution' and 'logs'."""
        from ignition_toolkit.api.routers.context import get_execution_context

        # Build a mock execution row
        mock_execution = MagicMock()
        mock_execution.execution_id = "abc-123"
        mock_execution.playbook_name = "Test Playbook"
        mock_execution.status = "completed"
        mock_execution.started_at = None
        mock_execution.completed_at = None
        mock_execution.error_message = None
        mock_execution.step_results = []
        mock_execution.execution_metadata = {}

        # Wire the session to return this execution
        mock_db._session.query.return_value.filter.return_value.first.return_value = mock_execution

        with patch(
            "ignition_toolkit.api.routers.context.get_database", return_value=mock_db
        ), patch(
            "ignition_toolkit.api.routers.context.get_log_capture", return_value=None
        ):
            result = asyncio.run(get_execution_context("abc-123"))

        assert "execution" in result
        assert "logs" in result
        assert result["execution"].execution_id == "abc-123"
        assert result["execution"].playbook_name == "Test Playbook"
        assert result["logs"] == []

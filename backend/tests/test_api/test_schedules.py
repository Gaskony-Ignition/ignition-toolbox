"""
Tests for schedule management API endpoints.

Tests list, get, create, delete, and toggle operations.
Uses direct function calls with mocking (same pattern as test_health.py).
"""

import asyncio
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_schedule(schedule_id: int = 1, name: str = "Test Schedule") -> MagicMock:
    """Return a mock ScheduledPlaybookModel with sensible defaults."""
    schedule = MagicMock()
    schedule.id = schedule_id
    schedule.name = name
    schedule.playbook_path = "playbooks/test.yaml"
    schedule.schedule_type = "interval"
    schedule.enabled = "true"
    schedule.to_dict.return_value = {
        "id": schedule_id,
        "name": name,
        "playbook_path": "playbooks/test.yaml",
        "schedule_type": "interval",
        "enabled": "true",
    }
    return schedule


def _make_db_with_result(scalar_result=None):
    """
    Build a mock database whose session returns *scalar_result* from
    ``result.scalar_one_or_none()`` and a list from ``result.scalars().all()``.
    """
    db = MagicMock()
    mock_session = MagicMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scalar_result
    if scalar_result is None:
        mock_result.scalars.return_value.all.return_value = []
    else:
        mock_result.scalars.return_value.all.return_value = [scalar_result]

    mock_session.execute.return_value = mock_result

    @contextmanager
    def session_scope():
        yield mock_session

    db.session_scope = session_scope
    db._session = mock_session
    return db


# ---------------------------------------------------------------------------
# list_schedules
# ---------------------------------------------------------------------------

class TestListSchedules:
    def test_list_schedules_returns_schedules_key(self):
        """GET /api/schedules returns a dict with 'schedules' key."""
        from ignition_toolkit.api.routers.schedules import list_schedules

        db = _make_db_with_result(None)  # empty database

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db):
            result = asyncio.run(list_schedules())

        assert "schedules" in result
        assert isinstance(result["schedules"], list)

    def test_list_schedules_returns_all_schedules(self):
        """GET /api/schedules serialises every schedule via to_dict()."""
        from ignition_toolkit.api.routers.schedules import list_schedules

        mock_schedule = _make_mock_schedule(1, "My Schedule")
        db = _make_db_with_result(mock_schedule)

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db):
            result = asyncio.run(list_schedules())

        assert len(result["schedules"]) == 1
        assert result["schedules"][0]["id"] == 1
        assert result["schedules"][0]["name"] == "My Schedule"

    def test_list_schedules_empty_database(self):
        """GET /api/schedules returns empty list when no schedules exist."""
        from ignition_toolkit.api.routers.schedules import list_schedules

        db = _make_db_with_result(None)

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db):
            result = asyncio.run(list_schedules())

        assert result["schedules"] == []


# ---------------------------------------------------------------------------
# get_schedule
# ---------------------------------------------------------------------------

class TestGetSchedule:
    def test_get_schedule_returns_schedule_dict(self):
        """GET /api/schedules/{id} returns schedule data when found."""
        from ignition_toolkit.api.routers.schedules import get_schedule

        mock_schedule = _make_mock_schedule(42, "Found Schedule")
        db = _make_db_with_result(mock_schedule)

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db):
            result = asyncio.run(get_schedule(42))

        assert result["id"] == 42
        assert result["name"] == "Found Schedule"

    def test_get_schedule_404_for_unknown_id(self):
        """GET /api/schedules/{id} raises 404 when schedule doesn't exist."""
        from ignition_toolkit.api.routers.schedules import get_schedule

        db = _make_db_with_result(None)  # schedule not found

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_schedule(999))

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# create_schedule
# ---------------------------------------------------------------------------

class TestCreateSchedule:
    def test_create_schedule_returns_success_message(self):
        """POST /api/schedules creates a schedule and returns success message."""
        from ignition_toolkit.api.routers.schedules import create_schedule, CreateScheduleRequest, ScheduleConfig

        mock_schedule = _make_mock_schedule(10, "New Schedule")
        mock_session = MagicMock()
        mock_session.flush.return_value = None
        mock_session.refresh.return_value = None
        mock_session.add.return_value = None

        # After flush/refresh, schedule has an id
        mock_schedule.id = 10
        mock_schedule.to_dict.return_value = {"id": 10, "name": "New Schedule"}

        db = MagicMock()

        @contextmanager
        def session_scope():
            # The create_schedule handler assigns schedule inside the block,
            # then calls .to_dict() on it. We need to make the constructor
            # return our mock. Patch ScheduledPlaybookModel instead.
            yield mock_session

        db.session_scope = session_scope

        mock_scheduler = MagicMock()
        mock_scheduler.add_schedule = AsyncMock(return_value=None)

        request = CreateScheduleRequest(
            name="New Schedule",
            playbook_path="playbooks/test.yaml",
            schedule_type="interval",
            schedule_config=ScheduleConfig(minutes=15),
            enabled=True,
        )

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db), \
             patch("ignition_toolkit.api.routers.schedules.get_scheduler", return_value=mock_scheduler), \
             patch("ignition_toolkit.api.routers.schedules.ScheduledPlaybookModel", return_value=mock_schedule):
            result = asyncio.run(create_schedule(request))

        assert result["message"] == "Schedule created successfully"
        assert "schedule" in result

    def test_create_schedule_calls_scheduler_when_enabled(self):
        """POST /api/schedules calls scheduler.add_schedule when enabled=True."""
        from ignition_toolkit.api.routers.schedules import create_schedule, CreateScheduleRequest, ScheduleConfig

        mock_schedule = _make_mock_schedule(11, "Enabled Schedule")
        mock_schedule.id = 11
        mock_session = MagicMock()

        db = MagicMock()

        @contextmanager
        def session_scope():
            yield mock_session

        db.session_scope = session_scope

        mock_scheduler = MagicMock()
        mock_scheduler.add_schedule = AsyncMock(return_value=None)

        request = CreateScheduleRequest(
            name="Enabled Schedule",
            playbook_path="playbooks/test.yaml",
            schedule_type="daily",
            schedule_config=ScheduleConfig(time="08:00"),
            enabled=True,
        )

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db), \
             patch("ignition_toolkit.api.routers.schedules.get_scheduler", return_value=mock_scheduler), \
             patch("ignition_toolkit.api.routers.schedules.ScheduledPlaybookModel", return_value=mock_schedule):
            asyncio.run(create_schedule(request))

        mock_scheduler.add_schedule.assert_awaited_once()

    def test_create_schedule_skips_scheduler_when_disabled(self):
        """POST /api/schedules does not add to scheduler when enabled=False."""
        from ignition_toolkit.api.routers.schedules import create_schedule, CreateScheduleRequest, ScheduleConfig

        mock_schedule = _make_mock_schedule(12, "Disabled Schedule")
        mock_schedule.id = 12
        mock_session = MagicMock()

        db = MagicMock()

        @contextmanager
        def session_scope():
            yield mock_session

        db.session_scope = session_scope

        mock_scheduler = MagicMock()
        mock_scheduler.add_schedule = AsyncMock(return_value=None)

        request = CreateScheduleRequest(
            name="Disabled Schedule",
            playbook_path="playbooks/test.yaml",
            schedule_type="interval",
            schedule_config=ScheduleConfig(minutes=60),
            enabled=False,
        )

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db), \
             patch("ignition_toolkit.api.routers.schedules.get_scheduler", return_value=mock_scheduler), \
             patch("ignition_toolkit.api.routers.schedules.ScheduledPlaybookModel", return_value=mock_schedule):
            asyncio.run(create_schedule(request))

        mock_scheduler.add_schedule.assert_not_awaited()


# ---------------------------------------------------------------------------
# delete_schedule
# ---------------------------------------------------------------------------

class TestDeleteSchedule:
    def test_delete_schedule_returns_success_message(self):
        """DELETE /api/schedules/{id} returns success message when found."""
        from ignition_toolkit.api.routers.schedules import delete_schedule

        mock_schedule = _make_mock_schedule(5, "Delete Me")
        db = _make_db_with_result(mock_schedule)

        mock_scheduler = MagicMock()
        mock_scheduler.remove_schedule = AsyncMock(return_value=None)

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db), \
             patch("ignition_toolkit.api.routers.schedules.get_scheduler", return_value=mock_scheduler):
            result = asyncio.run(delete_schedule(5))

        assert result["message"] == "Schedule deleted successfully"
        mock_scheduler.remove_schedule.assert_awaited_once_with(5)

    def test_delete_schedule_404_for_unknown_id(self):
        """DELETE /api/schedules/{id} raises 404 when schedule doesn't exist."""
        from ignition_toolkit.api.routers.schedules import delete_schedule

        db = _make_db_with_result(None)

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_schedule(999))

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# toggle_schedule
# ---------------------------------------------------------------------------

class TestToggleSchedule:
    def test_toggle_schedule_404_for_unknown_id(self):
        """POST /api/schedules/{id}/toggle raises 404 when schedule doesn't exist."""
        from ignition_toolkit.api.routers.schedules import toggle_schedule

        db = _make_db_with_result(None)

        with patch("ignition_toolkit.api.routers.schedules.get_database", return_value=db):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(toggle_schedule(999))

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Request model validation
# ---------------------------------------------------------------------------

class TestCreateScheduleRequestModel:
    def test_required_fields_present(self):
        """CreateScheduleRequest requires name, playbook_path, schedule_type, schedule_config."""
        from ignition_toolkit.api.routers.schedules import CreateScheduleRequest, ScheduleConfig

        req = CreateScheduleRequest(
            name="My Schedule",
            playbook_path="playbooks/foo.yaml",
            schedule_type="cron",
            schedule_config=ScheduleConfig(expression="0 * * * *"),
        )
        assert req.name == "My Schedule"
        assert req.playbook_path == "playbooks/foo.yaml"
        assert req.schedule_type == "cron"
        assert req.enabled is True  # default

    def test_schedule_config_fields(self):
        """ScheduleConfig accepts expression, minutes, time, day_of_week, day."""
        from ignition_toolkit.api.routers.schedules import ScheduleConfig

        cfg = ScheduleConfig(minutes=30)
        assert cfg.minutes == 30
        assert cfg.expression is None

        cfg2 = ScheduleConfig(expression="*/5 * * * *")
        assert cfg2.expression == "*/5 * * * *"

    def test_optional_parameters_default_none(self):
        """CreateScheduleRequest.parameters and gateway_url default to None."""
        from ignition_toolkit.api.routers.schedules import CreateScheduleRequest, ScheduleConfig

        req = CreateScheduleRequest(
            name="Minimal",
            playbook_path="playbooks/bar.yaml",
            schedule_type="daily",
            schedule_config=ScheduleConfig(time="09:00"),
        )
        assert req.parameters is None
        assert req.gateway_url is None
        assert req.credential_name is None


# ---------------------------------------------------------------------------
# get_next_runs
# ---------------------------------------------------------------------------

class TestGetNextRuns:
    def test_get_next_runs_returns_list(self):
        """GET /api/schedules/status/next-runs returns next_runs list."""
        from ignition_toolkit.api.routers.schedules import get_next_runs

        mock_scheduler = MagicMock()
        mock_scheduler.get_next_runs = AsyncMock(return_value=[
            {"schedule_id": 1, "next_run": "2026-02-22T10:00:00Z"},
        ])

        with patch("ignition_toolkit.api.routers.schedules.get_scheduler", return_value=mock_scheduler):
            result = asyncio.run(get_next_runs())

        assert "next_runs" in result
        assert len(result["next_runs"]) == 1

    def test_get_next_runs_empty_when_no_schedules(self):
        """GET /api/schedules/status/next-runs returns empty list when nothing scheduled."""
        from ignition_toolkit.api.routers.schedules import get_next_runs

        mock_scheduler = MagicMock()
        mock_scheduler.get_next_runs = AsyncMock(return_value=[])

        with patch("ignition_toolkit.api.routers.schedules.get_scheduler", return_value=mock_scheduler):
            result = asyncio.run(get_next_runs())

        assert result["next_runs"] == []

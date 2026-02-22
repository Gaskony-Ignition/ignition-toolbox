"""
Tests for update management API endpoints.

Tests check, status, and backups endpoints.
Uses direct function import + patch pattern.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


class TestCheckUpdates:
    def test_check_updates_returns_no_update_when_up_to_date(self):
        """GET /api/updates/check returns update_available=False when on latest."""
        from ignition_toolkit.api.routers.updates import check_updates

        with patch(
            "ignition_toolkit.api.routers.updates.check_for_updates",
            new=AsyncMock(return_value=None),
        ), patch(
            "ignition_toolkit.api.routers.updates.get_current_version",
            return_value="3.0.1",
        ):
            result = asyncio.run(check_updates())

        assert result.update_available is False
        assert result.current_version == "3.0.1"
        assert result.latest_version is None

    def test_check_updates_returns_update_info_when_available(self):
        """GET /api/updates/check returns full update info when a newer version exists."""
        from ignition_toolkit.api.routers.updates import check_updates

        update_info = {
            "current_version": "3.0.1",
            "latest_version": "3.1.0",
            "release_url": "https://github.com/test/releases/tag/v3.1.0",
            "release_notes": "Bug fixes and improvements",
            "download_url": "https://github.com/test/archive/v3.1.0.tar.gz",
            "published_at": "2026-01-01T00:00:00Z",
        }

        with patch(
            "ignition_toolkit.api.routers.updates.check_for_updates",
            new=AsyncMock(return_value=update_info),
        ):
            result = asyncio.run(check_updates())

        assert result.update_available is True
        assert result.current_version == "3.0.1"
        assert result.latest_version == "3.1.0"
        assert result.release_url == "https://github.com/test/releases/tag/v3.1.0"
        assert result.download_url == "https://github.com/test/archive/v3.1.0.tar.gz"
        assert result.published_at == "2026-01-01T00:00:00Z"

    def test_check_updates_response_has_required_fields(self):
        """GET /api/updates/check response always includes update_available and current_version."""
        from ignition_toolkit.api.routers.updates import check_updates

        with patch(
            "ignition_toolkit.api.routers.updates.check_for_updates",
            new=AsyncMock(return_value=None),
        ), patch(
            "ignition_toolkit.api.routers.updates.get_current_version",
            return_value="1.0.0",
        ):
            result = asyncio.run(check_updates())

        assert hasattr(result, "update_available")
        assert hasattr(result, "current_version")


class TestGetUpdateStatus:
    def test_get_update_status_returns_idle_by_default(self):
        """GET /api/updates/status returns idle status when no update is running."""
        from ignition_toolkit.api.routers.updates import get_update_status, update_status

        # Reset to idle state
        update_status["status"] = "idle"
        update_status["progress"] = 0
        update_status["message"] = "No update in progress"
        update_status["version"] = None
        update_status["error"] = None

        result = asyncio.run(get_update_status())

        assert result.status == "idle"
        assert result.progress == 0

    def test_get_update_status_returns_correct_structure(self):
        """GET /api/updates/status response has required fields."""
        from ignition_toolkit.api.routers.updates import get_update_status

        result = asyncio.run(get_update_status())

        assert hasattr(result, "status")
        assert hasattr(result, "progress")
        assert hasattr(result, "message")


class TestListBackups:
    def test_list_backups_returns_empty_list_when_no_backups(self):
        """GET /api/updates/backups returns empty list when no backups exist."""
        from ignition_toolkit.api.routers.updates import list_available_backups

        with patch(
            "ignition_toolkit.api.routers.updates.list_backups",
            return_value=[],
        ):
            result = asyncio.run(list_available_backups())

        assert "backups" in result
        assert result["backups"] == []

    def test_list_backups_returns_backup_info(self, tmp_path):
        """GET /api/updates/backups returns info for each backup directory."""
        from ignition_toolkit.api.routers.updates import list_available_backups

        backup_dir = tmp_path / "backup_20260101"
        backup_dir.mkdir()

        with patch(
            "ignition_toolkit.api.routers.updates.list_backups",
            return_value=[backup_dir],
        ):
            result = asyncio.run(list_available_backups())

        assert "backups" in result
        assert len(result["backups"]) == 1
        backup_entry = result["backups"][0]
        assert "name" in backup_entry
        assert "created_at" in backup_entry
        assert backup_entry["name"] == "backup_20260101"


class TestRollbackUpdate:
    def test_rollback_raises_404_when_no_backups(self):
        """POST /api/updates/rollback returns 404 when no backups are available."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.updates import rollback_update

        with patch(
            "ignition_toolkit.api.routers.updates.list_backups",
            return_value=[],
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(rollback_update())

        assert exc_info.value.status_code == 404

    def test_rollback_returns_success_when_backup_restored(self, tmp_path):
        """POST /api/updates/rollback returns success when restore succeeds."""
        from ignition_toolkit.api.routers.updates import rollback_update

        backup_dir = tmp_path / "backup_20260101"
        backup_dir.mkdir()

        with patch(
            "ignition_toolkit.api.routers.updates.list_backups",
            return_value=[backup_dir],
        ), patch(
            "ignition_toolkit.api.routers.updates.restore_backup",
            return_value=True,
        ):
            result = asyncio.run(rollback_update())

        assert result["status"] == "rollback_complete"
        assert "backup_used" in result

    def test_rollback_raises_500_when_restore_fails(self, tmp_path):
        """POST /api/updates/rollback returns 500 when restore fails."""
        from fastapi import HTTPException
        from ignition_toolkit.api.routers.updates import rollback_update

        backup_dir = tmp_path / "backup_20260101"
        backup_dir.mkdir()

        with patch(
            "ignition_toolkit.api.routers.updates.list_backups",
            return_value=[backup_dir],
        ), patch(
            "ignition_toolkit.api.routers.updates.restore_backup",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(rollback_update())

        assert exc_info.value.status_code == 500


class TestUpdateCheckResponseModel:
    def test_update_check_response_model_fields(self):
        """UpdateCheckResponse model can be instantiated with required fields."""
        from ignition_toolkit.api.routers.updates import UpdateCheckResponse

        response = UpdateCheckResponse(
            update_available=False,
            current_version="3.0.1",
        )
        assert response.update_available is False
        assert response.current_version == "3.0.1"
        assert response.latest_version is None

    def test_update_status_response_model_fields(self):
        """UpdateStatusResponse model can be instantiated with required fields."""
        from ignition_toolkit.api.routers.updates import UpdateStatusResponse

        response = UpdateStatusResponse(
            status="idle",
            progress=0,
            message="No update in progress",
        )
        assert response.status == "idle"
        assert response.progress == 0
        assert response.error is None

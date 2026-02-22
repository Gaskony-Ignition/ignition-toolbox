"""
Tests for playbook library API endpoints.

Tests browse, install, uninstall, update, and check-for-updates operations.
External HTTP calls are mocked with MagicMock / AsyncMock.

Note: PlaybookRegistry, PlaybookInstaller, and PlaybookUpdateChecker are
imported lazily inside each route function, so they must be patched at
their source module paths, not the router module.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(*, available=None):
    """
    Build a MagicMock PlaybookRegistry with sensible defaults.
    available: list of MagicMock AvailablePlaybook objects
    """
    registry = MagicMock()
    registry.get_available_playbooks.return_value = available or []
    registry.last_fetched = None
    registry.fetch_available_playbooks = AsyncMock()
    return registry


def _make_available_playbook(path: str = "gateway/module_upgrade"):
    pb = MagicMock()
    pb.playbook_path = path
    pb.version = "1.0"
    pb.domain = "gateway"
    pb.verified = True
    pb.verified_by = "test"
    pb.description = "A sample library playbook"
    pb.author = "Test Author"
    pb.tags = ["test"]
    pb.group = "testing"
    pb.size_bytes = 1024
    pb.dependencies = []
    pb.release_notes = None
    pb.download_url = "https://example.com/playbook.yaml"
    pb.checksum = "abc123"
    return pb


# ---------------------------------------------------------------------------
# browse_available_playbooks
# ---------------------------------------------------------------------------


class TestBrowseAvailablePlaybooks:
    def test_browse_returns_success_with_list(self):
        """GET /library/browse returns status=success and a playbooks list."""
        from ignition_toolkit.api.routers.playbook_library import browse_available_playbooks

        mock_registry = _make_registry(available=[])

        with patch(
            "ignition_toolkit.playbook.registry.PlaybookRegistry",
            return_value=mock_registry,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookRegistry",
            return_value=mock_registry,
            create=True,
        ):
            result = asyncio.run(browse_available_playbooks())

        assert result["status"] == "success"
        assert isinstance(result["playbooks"], list)
        assert result["count"] == 0

    def test_browse_returns_playbooks_when_available(self):
        """browse returns the playbooks returned by the registry."""
        from ignition_toolkit.api.routers.playbook_library import browse_available_playbooks

        available = [_make_available_playbook("gateway/module_upgrade")]
        mock_registry = _make_registry(available=available)

        with patch(
            "ignition_toolkit.playbook.registry.PlaybookRegistry",
            return_value=mock_registry,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookRegistry",
            return_value=mock_registry,
            create=True,
        ):
            result = asyncio.run(browse_available_playbooks())

        assert result["count"] == 1
        assert result["playbooks"][0]["playbook_path"] == "gateway/module_upgrade"

    def test_browse_continues_when_fetch_fails(self):
        """If the remote fetch fails, browse still returns an empty list."""
        from ignition_toolkit.api.routers.playbook_library import browse_available_playbooks

        mock_registry = _make_registry(available=[])
        mock_registry.fetch_available_playbooks = AsyncMock(
            side_effect=ConnectionError("GitHub unreachable")
        )

        with patch(
            "ignition_toolkit.playbook.registry.PlaybookRegistry",
            return_value=mock_registry,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookRegistry",
            return_value=mock_registry,
            create=True,
        ):
            result = asyncio.run(browse_available_playbooks())

        assert result["status"] == "success"
        assert result["count"] == 0

    def test_browse_empty_returns_message(self):
        """An empty library includes a human-readable message."""
        from ignition_toolkit.api.routers.playbook_library import browse_available_playbooks

        mock_registry = _make_registry(available=[])

        with patch(
            "ignition_toolkit.playbook.registry.PlaybookRegistry",
            return_value=mock_registry,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookRegistry",
            return_value=mock_registry,
            create=True,
        ):
            result = asyncio.run(browse_available_playbooks())

        assert result["message"] is not None


# ---------------------------------------------------------------------------
# install_playbook
# ---------------------------------------------------------------------------


class TestInstallPlaybook:
    def test_install_already_installed_raises_400(self):
        """Installing an already-installed playbook raises 400 (PlaybookInstallError)."""
        from ignition_toolkit.api.routers.playbook_library import install_playbook, PlaybookInstallRequest
        from ignition_toolkit.playbook.installer import PlaybookInstallError

        mock_installer = MagicMock()
        mock_installer.install_playbook = AsyncMock(
            side_effect=PlaybookInstallError("Playbook already installed")
        )

        request = PlaybookInstallRequest(
            playbook_path="gateway/module_upgrade",
            version="latest",
            verify_checksum=False,
        )

        with patch(
            "ignition_toolkit.playbook.installer.PlaybookInstaller",
            return_value=mock_installer,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookInstaller",
            return_value=mock_installer,
            create=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(install_playbook(request))

        assert exc_info.value.status_code == 400

    def test_install_not_found_in_repo_raises_400(self):
        """Installing a playbook that is not in the registry raises 400."""
        from ignition_toolkit.api.routers.playbook_library import install_playbook, PlaybookInstallRequest
        from ignition_toolkit.playbook.installer import PlaybookInstallError

        mock_installer = MagicMock()
        mock_installer.install_playbook = AsyncMock(
            side_effect=PlaybookInstallError("Playbook not found in repository")
        )

        request = PlaybookInstallRequest(
            playbook_path="gateway/nonexistent",
        )

        with patch(
            "ignition_toolkit.playbook.installer.PlaybookInstaller",
            return_value=mock_installer,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookInstaller",
            return_value=mock_installer,
            create=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(install_playbook(request))

        assert exc_info.value.status_code == 400

    def test_install_success_returns_success(self, tmp_path):
        """A successful installation returns status=success."""
        from ignition_toolkit.api.routers.playbook_library import install_playbook, PlaybookInstallRequest

        installed_path = tmp_path / "gateway" / "module_upgrade.yaml"
        installed_path.parent.mkdir(parents=True)
        installed_path.touch()

        mock_installer = MagicMock()
        mock_installer.install_playbook = AsyncMock(return_value=installed_path)

        request = PlaybookInstallRequest(
            playbook_path="gateway/module_upgrade",
        )

        with patch(
            "ignition_toolkit.playbook.installer.PlaybookInstaller",
            return_value=mock_installer,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookInstaller",
            return_value=mock_installer,
            create=True,
        ):
            result = asyncio.run(install_playbook(request))

        assert result["status"] == "success"
        assert result["playbook_path"] == "gateway/module_upgrade"

    def test_install_request_model_requires_playbook_path(self):
        """PlaybookInstallRequest requires playbook_path."""
        from ignition_toolkit.api.routers.playbook_library import PlaybookInstallRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PlaybookInstallRequest()


# ---------------------------------------------------------------------------
# uninstall_playbook
# ---------------------------------------------------------------------------


class TestUninstallPlaybook:
    def test_uninstall_not_installed_raises_404(self):
        """Uninstalling a playbook that is not installed returns 404."""
        from ignition_toolkit.api.routers.playbook_library import uninstall_playbook

        mock_installer = MagicMock()
        mock_installer.uninstall_playbook = AsyncMock(return_value=False)  # not found

        with patch(
            "ignition_toolkit.playbook.installer.PlaybookInstaller",
            return_value=mock_installer,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookInstaller",
            return_value=mock_installer,
            create=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(uninstall_playbook("gateway/nonexistent"))

        assert exc_info.value.status_code == 404

    def test_uninstall_builtin_without_force_raises_400(self):
        """Uninstalling a built-in playbook without force raises 400 (PlaybookInstallError)."""
        from ignition_toolkit.api.routers.playbook_library import uninstall_playbook
        from ignition_toolkit.playbook.installer import PlaybookInstallError

        mock_installer = MagicMock()
        mock_installer.uninstall_playbook = AsyncMock(
            side_effect=PlaybookInstallError("Cannot uninstall built-in playbook")
        )

        with patch(
            "ignition_toolkit.playbook.installer.PlaybookInstaller",
            return_value=mock_installer,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookInstaller",
            return_value=mock_installer,
            create=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(uninstall_playbook("gateway/module_upgrade", force=False))

        assert exc_info.value.status_code == 400

    def test_uninstall_success_returns_success(self):
        """Successful uninstall returns status=success."""
        from ignition_toolkit.api.routers.playbook_library import uninstall_playbook

        mock_installer = MagicMock()
        mock_installer.uninstall_playbook = AsyncMock(return_value=True)

        with patch(
            "ignition_toolkit.playbook.installer.PlaybookInstaller",
            return_value=mock_installer,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookInstaller",
            return_value=mock_installer,
            create=True,
        ):
            result = asyncio.run(uninstall_playbook("gateway/module_upgrade"))

        assert result["status"] == "success"
        assert result["playbook_path"] == "gateway/module_upgrade"


# ---------------------------------------------------------------------------
# check_for_updates
# ---------------------------------------------------------------------------


class TestCheckForUpdates:
    def test_check_for_updates_returns_success(self):
        """GET /library/updates returns status=success and update details."""
        from ignition_toolkit.api.routers.playbook_library import check_for_updates

        mock_result = MagicMock()
        mock_result.updates = []
        mock_result.checked_at = "2026-01-01T00:00:00"
        mock_result.total_playbooks = 0
        mock_result.updates_available = 0
        mock_result.has_updates = False
        mock_result.last_fetched = None
        mock_result.major_updates = []
        mock_result.minor_updates = []

        mock_checker = MagicMock()
        mock_checker.refresh = AsyncMock()
        mock_checker.check_for_updates.return_value = mock_result

        with patch(
            "ignition_toolkit.playbook.update_checker.PlaybookUpdateChecker",
            return_value=mock_checker,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookUpdateChecker",
            return_value=mock_checker,
            create=True,
        ):
            result = asyncio.run(check_for_updates())

        assert result["status"] == "success"
        assert isinstance(result["updates"], list)
        assert result["has_updates"] is False

    def test_check_for_updates_with_updates_available(self):
        """When updates are available, they appear in the response."""
        from ignition_toolkit.api.routers.playbook_library import check_for_updates

        update = MagicMock()
        update.playbook_path = "gateway/module_upgrade"
        update.current_version = "1.0"
        update.latest_version = "2.0"
        update.description = "Major update"
        update.release_notes = "What's new"
        update.domain = "gateway"
        update.verified = True
        update.verified_by = "test"
        update.size_bytes = 1024
        update.author = "Test"
        update.tags = []
        update.is_major_update = True
        update.version_diff = "1.0 → 2.0"
        update.download_url = "https://example.com/playbook.yaml"
        update.checksum = "abc123"

        mock_result = MagicMock()
        mock_result.updates = [update]
        mock_result.checked_at = "2026-01-01T00:00:00"
        mock_result.total_playbooks = 1
        mock_result.updates_available = 1
        mock_result.has_updates = True
        mock_result.last_fetched = None
        mock_result.major_updates = [update]
        mock_result.minor_updates = []

        mock_checker = MagicMock()
        mock_checker.refresh = AsyncMock()
        mock_checker.check_for_updates.return_value = mock_result

        with patch(
            "ignition_toolkit.playbook.update_checker.PlaybookUpdateChecker",
            return_value=mock_checker,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookUpdateChecker",
            return_value=mock_checker,
            create=True,
        ):
            result = asyncio.run(check_for_updates())

        assert result["has_updates"] is True
        assert len(result["updates"]) == 1
        assert result["updates"][0]["playbook_path"] == "gateway/module_upgrade"

    def test_check_for_updates_error_raises_500(self):
        """Unexpected errors during update check raise 500."""
        from ignition_toolkit.api.routers.playbook_library import check_for_updates

        mock_checker = MagicMock()
        mock_checker.refresh = AsyncMock(side_effect=RuntimeError("network error"))

        with patch(
            "ignition_toolkit.playbook.update_checker.PlaybookUpdateChecker",
            return_value=mock_checker,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookUpdateChecker",
            return_value=mock_checker,
            create=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(check_for_updates())

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# check_playbook_update (single playbook)
# ---------------------------------------------------------------------------


class TestCheckPlaybookUpdate:
    def test_no_update_returns_has_update_false(self):
        """When no update is available for a specific playbook, has_update=False."""
        from ignition_toolkit.api.routers.playbook_library import check_playbook_update

        mock_checker = MagicMock()
        mock_checker.get_update.return_value = None

        with patch(
            "ignition_toolkit.playbook.update_checker.PlaybookUpdateChecker",
            return_value=mock_checker,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookUpdateChecker",
            return_value=mock_checker,
            create=True,
        ):
            result = asyncio.run(check_playbook_update("gateway/module_upgrade"))

        assert result["has_update"] is False
        assert result["status"] == "success"

    def test_update_available_returns_details(self):
        """When an update is available, the response includes version details."""
        from ignition_toolkit.api.routers.playbook_library import check_playbook_update

        update = MagicMock()
        update.playbook_path = "gateway/module_upgrade"
        update.current_version = "1.0"
        update.latest_version = "1.1"
        update.description = "Minor fix"
        update.release_notes = "Bug fixes"
        update.domain = "gateway"
        update.verified = False
        update.verified_by = None
        update.size_bytes = 512
        update.author = "Test"
        update.tags = []
        update.is_major_update = False
        update.version_diff = "1.0 → 1.1"

        mock_checker = MagicMock()
        mock_checker.get_update.return_value = update

        with patch(
            "ignition_toolkit.playbook.update_checker.PlaybookUpdateChecker",
            return_value=mock_checker,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookUpdateChecker",
            return_value=mock_checker,
            create=True,
        ):
            result = asyncio.run(check_playbook_update("gateway/module_upgrade"))

        assert result["has_update"] is True
        assert result["latest_version"] == "1.1"


# ---------------------------------------------------------------------------
# update_playbook_to_latest
# ---------------------------------------------------------------------------


class TestUpdatePlaybookToLatest:
    def test_update_not_installed_raises_400(self):
        """Updating a playbook that is not installed raises 400 (PlaybookInstallError)."""
        from ignition_toolkit.api.routers.playbook_library import update_playbook_to_latest
        from ignition_toolkit.playbook.installer import PlaybookInstallError

        mock_installer = MagicMock()
        mock_installer.update_playbook = AsyncMock(
            side_effect=PlaybookInstallError("Playbook is not installed")
        )

        with patch(
            "ignition_toolkit.playbook.installer.PlaybookInstaller",
            return_value=mock_installer,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookInstaller",
            return_value=mock_installer,
            create=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(update_playbook_to_latest("gateway/nonexistent"))

        assert exc_info.value.status_code == 400

    def test_update_success_returns_success(self, tmp_path):
        """Successful update returns status=success."""
        from ignition_toolkit.api.routers.playbook_library import update_playbook_to_latest

        updated_path = tmp_path / "gateway" / "module_upgrade.yaml"
        updated_path.parent.mkdir(parents=True)
        updated_path.touch()

        mock_installer = MagicMock()
        mock_installer.update_playbook = AsyncMock(return_value=updated_path)

        with patch(
            "ignition_toolkit.playbook.installer.PlaybookInstaller",
            return_value=mock_installer,
        ), patch(
            "ignition_toolkit.api.routers.playbook_library.PlaybookInstaller",
            return_value=mock_installer,
            create=True,
        ):
            result = asyncio.run(update_playbook_to_latest("gateway/module_upgrade"))

        assert result["status"] == "success"
        assert result["playbook_path"] == "gateway/module_upgrade"

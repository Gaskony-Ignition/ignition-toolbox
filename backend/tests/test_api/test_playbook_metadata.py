"""
Tests for playbook metadata API endpoints.

Tests mark_verified, unmark_verified, enable, disable, and reset operations.
Uses direct function calls with asyncio.run() and mocking.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_metadata_store(*, verified: bool = False, enabled: bool = True):
    """Return a MagicMock metadata store with sensible defaults."""
    store = MagicMock()

    meta = MagicMock()
    meta.verified = verified
    meta.verified_at = "2026-01-01T00:00:00" if verified else None
    meta.enabled = enabled

    store.get_metadata.return_value = meta
    return store


def _make_path_validator(relative_path: str = "gateway/test.yaml"):
    """Patch get_relative_playbook_path to return a safe relative path."""
    return patch(
        "ignition_toolkit.api.routers.playbook_metadata.get_relative_playbook_path",
        return_value=relative_path,
    )


# ---------------------------------------------------------------------------
# mark_playbook_verified
# ---------------------------------------------------------------------------


class TestMarkPlaybookVerified:
    def test_verify_returns_verified_true(self):
        """Marking a playbook as verified returns verified=True."""
        from ignition_toolkit.api.routers.playbook_metadata import mark_playbook_verified

        mock_store = _make_metadata_store(verified=True)

        with _make_path_validator(), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(mark_playbook_verified("gateway/test.yaml"))

        assert result["status"] == "success"
        assert result["verified"] is True
        mock_store.mark_verified.assert_called_once_with("gateway/test.yaml", verified_by="user")

    def test_verify_error_raises_500(self):
        """An unexpected exception from the store raises a 500."""
        from ignition_toolkit.api.routers.playbook_metadata import mark_playbook_verified

        mock_store = MagicMock()
        mock_store.mark_verified.side_effect = RuntimeError("store failure")

        with _make_path_validator(), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(mark_playbook_verified("gateway/test.yaml"))

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# unmark_playbook_verified
# ---------------------------------------------------------------------------


class TestUnmarkPlaybookVerified:
    def test_unverify_returns_verified_false(self):
        """Unmarking a playbook returns verified=False."""
        from ignition_toolkit.api.routers.playbook_metadata import unmark_playbook_verified

        mock_store = _make_metadata_store(verified=False)

        with _make_path_validator(), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(unmark_playbook_verified("gateway/test.yaml"))

        assert result["status"] == "success"
        assert result["verified"] is False
        mock_store.unmark_verified.assert_called_once_with("gateway/test.yaml")

    def test_unverify_error_raises_500(self):
        """An unexpected exception from the store raises a 500."""
        from ignition_toolkit.api.routers.playbook_metadata import unmark_playbook_verified

        mock_store = MagicMock()
        mock_store.unmark_verified.side_effect = RuntimeError("store failure")

        with _make_path_validator(), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(unmark_playbook_verified("gateway/test.yaml"))

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# enable_playbook
# ---------------------------------------------------------------------------


class TestEnablePlaybook:
    def test_enable_returns_enabled_true(self):
        """Enabling a playbook returns enabled=True."""
        from ignition_toolkit.api.routers.playbook_metadata import enable_playbook

        mock_store = _make_metadata_store(enabled=True)

        with _make_path_validator(), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(enable_playbook("gateway/test.yaml"))

        assert result["status"] == "success"
        assert result["enabled"] is True
        mock_store.set_enabled.assert_called_once_with("gateway/test.yaml", True)

    def test_enable_error_raises_500(self):
        """An unexpected exception from the store raises a 500."""
        from ignition_toolkit.api.routers.playbook_metadata import enable_playbook

        mock_store = MagicMock()
        mock_store.set_enabled.side_effect = RuntimeError("store failure")

        with _make_path_validator(), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(enable_playbook("gateway/test.yaml"))

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# disable_playbook
# ---------------------------------------------------------------------------


class TestDisablePlaybook:
    def test_disable_returns_enabled_false(self):
        """Disabling a playbook returns enabled=False."""
        from ignition_toolkit.api.routers.playbook_metadata import disable_playbook

        mock_store = _make_metadata_store(enabled=False)

        with _make_path_validator(), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(disable_playbook("gateway/test.yaml"))

        assert result["status"] == "success"
        assert result["enabled"] is False
        mock_store.set_enabled.assert_called_once_with("gateway/test.yaml", False)

    def test_disable_error_raises_500(self):
        """An unexpected exception from the store raises a 500."""
        from ignition_toolkit.api.routers.playbook_metadata import disable_playbook

        mock_store = MagicMock()
        mock_store.set_enabled.side_effect = RuntimeError("store failure")

        with _make_path_validator(), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(disable_playbook("gateway/test.yaml"))

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# reset_all_metadata
# ---------------------------------------------------------------------------


class TestResetAllMetadata:
    def test_reset_all_calls_reset_on_store(self):
        """reset_all_metadata calls reset_all() on the metadata store."""
        from ignition_toolkit.api.routers.playbook_metadata import reset_all_metadata

        mock_store = _make_metadata_store()

        with patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(reset_all_metadata())

        assert result["status"] == "success"
        mock_store.reset_all.assert_called_once()

    def test_reset_all_error_raises_500(self):
        """An unexpected exception from the store raises a 500."""
        from ignition_toolkit.api.routers.playbook_metadata import reset_all_metadata

        mock_store = MagicMock()
        mock_store.reset_all.side_effect = RuntimeError("store failure")

        with patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(reset_all_metadata())

        assert exc_info.value.status_code == 500

    def test_reset_all_returns_message(self):
        """reset_all_metadata includes a human-readable message."""
        from ignition_toolkit.api.routers.playbook_metadata import reset_all_metadata

        mock_store = _make_metadata_store()

        with patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_metadata_store",
            return_value=mock_store,
        ):
            result = asyncio.run(reset_all_metadata())

        assert "message" in result
        assert "reset" in result["message"].lower()


# ---------------------------------------------------------------------------
# get_relative_playbook_path (unit tests for the helper itself)
# ---------------------------------------------------------------------------


class TestGetRelativePlaybookPath:
    def test_absolute_path_rejected(self):
        """An absolute path outside playbook dirs raises 400."""
        from ignition_toolkit.api.routers.playbook_metadata import get_relative_playbook_path

        # get_all_playbook_dirs is imported inside the function, so patch at source
        with patch(
            "ignition_toolkit.core.paths.get_all_playbook_dirs",
            return_value=[],
        ), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_all_playbook_dirs",
            return_value=[],
            create=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_relative_playbook_path("/etc/passwd")

        assert exc_info.value.status_code == 400

    def test_traversal_path_rejected(self):
        """A path containing .. is rejected with 400."""
        from ignition_toolkit.api.routers.playbook_metadata import get_relative_playbook_path

        with patch(
            "ignition_toolkit.core.paths.get_all_playbook_dirs",
            return_value=[],
        ), patch(
            "ignition_toolkit.api.routers.playbook_metadata.get_all_playbook_dirs",
            return_value=[],
            create=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_relative_playbook_path("../../etc/passwd")

        assert exc_info.value.status_code == 400
